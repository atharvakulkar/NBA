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
            "fax_received",
            "extracting_information",
            "needs_review",
            "missing_information",
            "ready_for_assignment",
            "assigned_to_care_team",
            "completed",
            "rejected",
        ]

        transitions = [
            # Core linear flow.
            {"trigger": "start_extraction", "source": "fax_received", "dest": "extracting_information"},
            {"trigger": "submit_for_review", "source": "extracting_information", "dest": "needs_review"},
            # Router-controlled outcomes (auto-routed).
            {"trigger": "route_to_missing_information", "source": "needs_review", "dest": "missing_information"},
            {"trigger": "route_to_ready_for_assignment", "source": "needs_review", "dest": "ready_for_assignment"},
            # Missing info remediation.
            {"trigger": "mark_info_received", "source": "missing_information", "dest": "needs_review"},
            # Assignment + completion.
            {"trigger": "assign_to_care_team", "source": "ready_for_assignment", "dest": "assigned_to_care_team"},
            {"trigger": "complete", "source": "assigned_to_care_team", "dest": "completed"},
            # Reject paths.
            {
                "trigger": "reject",
                "source": ["extracting_information", "needs_review", "missing_information", "ready_for_assignment"],
                "dest": "rejected",
            },
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
            ("extracting_information", "needs_review"): "submit_for_review",
            ("extracting_information", "rejected"): "reject",
            ("needs_review", "missing_information"): "route_to_missing_information",
            ("needs_review", "ready_for_assignment"): "route_to_ready_for_assignment",
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
            # Linear flow actions (optional).
            "start_extraction": "start_extraction",
            "submit_for_review": "submit_for_review",
            # Missing-info actions: we treat these as "info received" signals.
            "request_patient_name": "mark_info_received",
            "request_insurance": "mark_info_received",
            "request_contact_number": "mark_info_received",
            "request_missing_information": "mark_info_received",
            # Demo prototype: "provide_*" actions behave like info received.
            "provide_patient_name": "mark_info_received",
            "provide_insurance": "mark_info_received",
            "provide_contact_number": "mark_info_received",
            # Assignment/completion.
            "assign_to_care_team": "assign_to_care_team",
            "complete": "complete",
            # Reject.
            "reject": "reject",
        }

        trigger = action_to_trigger.get(action)
        if not trigger:
            raise InvalidActionError(f"Unknown action: {action}")

        if not hasattr(self, trigger):
            raise InvalidActionError(f"Invalid action trigger: {trigger}")

        getattr(self, trigger)()

