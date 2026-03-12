from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from transitions import Machine

from .models import ReferralRecord, ReferralState


TransitionEdge = Tuple[ReferralState, ReferralState]


class InvalidActionError(RuntimeError):
    pass


@dataclass
class ReferralStateMachine:
    """
    `transitions` state machine wrapper.

    The machine triggers `on_state_change` after every transition; callers can attach
    a router callback that computes the correct next state and optionally auto-advances.
    """

    record: ReferralRecord
    on_state_change: Optional[Callable[[ReferralRecord], Optional[ReferralState]]] = None
    transitions: List[TransitionEdge] = field(init=False, default_factory=list)
    state: ReferralState = field(init=False)
    _machine: Machine = field(init=False, repr=False)

    def __post_init__(self) -> None:
        # `transitions` requires a writable `state` attribute on the model.
        self.state: ReferralState = self.record.state

        states: Sequence[ReferralState] = [
            "referral_received",
            "completed",
            "needs_review",
            "incomplete",
            "rejected",
        ]

        transitions = [
            # From referral_received, route to one of four states.
            {"trigger": "route_to_completed", "source": "referral_received", "dest": "completed"},
            {"trigger": "route_to_needs_review", "source": "referral_received", "dest": "needs_review"},
            {"trigger": "route_to_incomplete", "source": "referral_received", "dest": "incomplete"},
            {"trigger": "route_to_rejected", "source": "referral_received", "dest": "rejected"},
            # From needs_review and incomplete, can go back to referral_received.
            {"trigger": "return_to_referral_received", "source": ["needs_review", "incomplete"], "dest": "referral_received"},
        ]

        self._machine = Machine(
            model=self,
            states=states,
            transitions=transitions,
            initial=self.state,
            after_state_change="_after_state_change",
            send_event=True,
            ignore_invalid_triggers=True,
        )

        # Cache edges for diagram export.
        for t in transitions:
            src = t["source"]
            dst = t["dest"]
            if isinstance(src, list):
                for s in src:
                    self.transitions.append((s, dst))
            else:
                self.transitions.append((src, dst))

    def _after_state_change(self, event) -> None:  # transitions callback signature
        self.record.state = self.state  # keep record in sync

        if self.on_state_change:
            next_state = self.on_state_change(self.record)
            if next_state and next_state != self.record.state:
                self._auto_advance(next_state)

    def _auto_advance(self, next_state: ReferralState) -> None:
        # Map destination to trigger names for router-controlled branch points.
        mapping: Dict[tuple[ReferralState, ReferralState], str] = {
            ("referral_received", "completed"): "route_to_completed",
            ("referral_received", "needs_review"): "route_to_needs_review",
            ("referral_received", "incomplete"): "route_to_incomplete",
            ("referral_received", "rejected"): "route_to_rejected",
            ("needs_review", "referral_received"): "return_to_referral_received",
            ("incomplete", "referral_received"): "return_to_referral_received",
        }
        trigger = mapping.get((self.record.state, next_state))
        if trigger and hasattr(self, trigger):
            getattr(self, trigger)()

    def apply_routing(self) -> None:
        """
        Ask the router (if configured) for the correct next state and auto-advance
        when applicable.
        """

        if not self.on_state_change:
            return
        next_state = self.on_state_change(self.record)
        if next_state and next_state != self.record.state:
            self._auto_advance(next_state)

    def execute_action(self, action: str) -> None:
        """
        Execute an external action by mapping to an internal trigger.

        This keeps API contracts stable even if internal triggers change.
        """

        action_to_trigger = {
            # Routing actions from referral_received.
            "route_to_completed": "route_to_completed",
            "route_to_needs_review": "route_to_needs_review",
            "route_to_incomplete": "route_to_incomplete",
            "route_to_rejected": "route_to_rejected",
            # Return to referral_received from needs_review or incomplete.
            "return_to_referral_received": "return_to_referral_received",
            # Alternative action names for convenience.
            "complete": "route_to_completed",
            "mark_for_review": "route_to_needs_review",
            "mark_incomplete": "route_to_incomplete",
            "reject": "route_to_rejected",
            "return_to_received": "return_to_referral_received",
        }

        trigger = action_to_trigger.get(action)
        if not trigger:
            raise InvalidActionError(f"Unknown action: {action}")

        if not hasattr(self, trigger):
            raise InvalidActionError(f"Invalid action trigger: {trigger}")

        getattr(self, trigger)()

