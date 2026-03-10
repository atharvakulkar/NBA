from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

from .models import ReferralState


TransitionEdge = Tuple[ReferralState, ReferralState]


@dataclass(slots=True)
class MermaidGenerator:
    """Generates Mermaid `stateDiagram-v2` strings for the referral workflow."""

    def generate(self, edges: Sequence[TransitionEdge], current_state: ReferralState) -> str:
        lines: List[str] = ["stateDiagram-v2"]

        # Explicit start node.
        lines.append("    [*] --> fax_received")

        for src, dst in edges:
            lines.append(f"    {src} --> {dst}")

        # Determine "completed" states along the main linear flow.
        main_flow: List[ReferralState] = [
            "fax_received",
            "extracting_information",
            "needs_review",
            "missing_information",
            "ready_for_assignment",
            "assigned_to_care_team",
            "completed",
        ]

        completed_states: List[ReferralState] = []
        if current_state == "rejected":
            # For rejection scenarios (e.g., Aetna after extracting_information),
            # show the upstream happy-path states as completed up to extraction.
            completed_states = ["fax_received", "extracting_information"]
        elif current_state in main_flow:
            idx = main_flow.index(current_state)
            completed_states = main_flow[:idx]

        lines.append("")

        # Style completed states in green.
        for state in completed_states:
            lines.append(f"    style {state} fill:#e6ffed,stroke:#28a745,stroke-width:1.5px")

        # Highlight current state:
        # - red for rejected
        # - yellow for all other states
        if current_state == "rejected":
            lines.append(f"    style {current_state} fill:#ffe6e6,stroke:#cc0000,stroke-width:3px")
        else:
            lines.append(f"    style {current_state} fill:#fffbdd,stroke:#b58900,stroke-width:2px")
        return "\n".join(lines)

