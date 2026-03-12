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
        lines.append("    [*] --> referral_received")

        # Add transitions from referral_received to the four destination states.
        # We'll add all four transitions explicitly for clarity.
        destination_states = ["completed", "needs_review", "incomplete", "rejected"]
        for dst in destination_states:
            lines.append(f"    referral_received --> {dst}")

        # Add transitions from needs_review and incomplete back to referral_received.
        lines.append("    needs_review --> referral_received")
        lines.append("    incomplete --> referral_received")

        # Also add any additional edges that might exist (for future extensibility).
        for src, dst in edges:
            # Skip edges we've already added explicitly
            if (src == "referral_received" and dst in destination_states) or \
               (src in ["needs_review", "incomplete"] and dst == "referral_received"):
                continue
            lines.append(f"    {src} --> {dst}")

        lines.append("")

        # Style logic:
        # - If current state is referral_received, it's the starting point (yellow)
        # - If current state is completed, referral_received is completed (green), completed is current (yellow)
        # - If current state is needs_review, referral_received is completed (green), needs_review is current (yellow)
        # - If current state is incomplete, referral_received is completed (green), incomplete is current (yellow)
        # - If current state is rejected, referral_received is completed (green), rejected is current (red)

        if current_state == "referral_received":
            # Starting state - highlight in yellow
            lines.append(f"    style {current_state} fill:#fffbdd,stroke:#b58900,stroke-width:2px")
        else:
            # referral_received is always completed when we're in any other state
            lines.append("    style referral_received fill:#e6ffed,stroke:#28a745,stroke-width:1.5px")
            
            # Highlight current state
            if current_state == "rejected":
                lines.append(f"    style {current_state} fill:#ffe6e6,stroke:#cc0000,stroke-width:3px")
            elif current_state == "completed":
                lines.append(f"    style {current_state} fill:#e6ffed,stroke:#28a745,stroke-width:2px")
            else:
                lines.append(f"    style {current_state} fill:#fffbdd,stroke:#b58900,stroke-width:2px")
        
        return "\n".join(lines)

