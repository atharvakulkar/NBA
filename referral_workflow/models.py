from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Sequence

from pydantic import BaseModel, Field


ReferralState = Literal[
    "referral_received",
    "completed",
    "needs_review",
    "incomplete",
    "rejected",
]


class ChecklistItem(BaseModel):
    """Single rule evaluation result."""

    rule: str
    status: Literal["passed", "failed"]


class NextBestAction(BaseModel):
    """Suggested action to unblock the referral workflow."""

    action: str
    reason: Optional[str] = None


class WorkflowPayload(BaseModel):
    """Final, JSON-serializable workflow payload returned by the engine/API."""

    current_state: ReferralState
    attributes: Dict[str, Any] = Field(default_factory=dict)
    missing_fields: List[str] = Field(default_factory=list)
    checklist: List[ChecklistItem] = Field(default_factory=list)
    next_best_actions: List[NextBestAction] = Field(default_factory=list)
    mermaid_diagram: str


class ActionRequest(BaseModel):
    """API request payload to execute a workflow action."""

    action: str
    data: Dict[str, Any] = Field(default_factory=dict)


class MermaidResponse(BaseModel):
    diagram: str


class MermaidUpdateRequest(BaseModel):
    """API request payload to save a custom Mermaid diagram."""

    diagram: str


@dataclass(slots=True)
class ReferralRecord:
    """
    In-memory representation of a referral.

    In production, replace this with your ORM entity and store in a database.
    """

    referral_id: str
    state: ReferralState = "referral_received"
    attributes: Dict[str, Any] = field(default_factory=dict)
    custom_mermaid_diagram: Optional[str] = None

    def get_attr(self, name: str) -> Any:
        return self.attributes.get(name)

    def set_attr(self, name: str, value: Any) -> None:
        self.attributes[name] = value


@dataclass(slots=True)
class RuleDefinition:
    name: str
    condition: str


@dataclass(slots=True)
class RuleSet:
    rules: Sequence[RuleDefinition]
    success_state: ReferralState
    failure_state: ReferralState


@dataclass(slots=True)
class RuleEvaluation:
    checklist: List[ChecklistItem]
    passed: bool
    failed_rule_names: List[str]
    missing_fields: List[str]
    success_state: Optional[ReferralState] = None
    failure_state: Optional[ReferralState] = None

