from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .models import NextBestAction


@dataclass(slots=True)
class NextBestActionEngine:
    """
    Generates Next Best Actions based on missing fields.

    This is intentionally simple and deterministic. In production, you can:
    - load mappings from config/DB
    - incorporate payer-specific logic
    - incorporate channel preferences + SLAs
    """

    field_to_action: Dict[str, str]

    @classmethod
    def default(cls) -> "NextBestActionEngine":
        return cls(
            field_to_action={
                "patient_name": "request_patient_name",
                "insurance": "request_insurance",
                "contact_number": "request_contact_number",
            }
        )

    def generate(self, missing_fields: List[str]) -> List[NextBestAction]:
        actions: List[NextBestAction] = []
        for f in missing_fields:
            a = self.field_to_action.get(f)
            if a:
                actions.append(NextBestAction(action=a, reason=f"Missing field: {f}"))
            else:
                actions.append(NextBestAction(action="request_missing_information", reason=f"Missing field: {f}"))
        return actions

