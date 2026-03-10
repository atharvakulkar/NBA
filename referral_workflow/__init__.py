"""
Hospice Referral Intake workflow engine.

This package provides:
- A `transitions`-based state machine
- JSON-configured rules and checklist evaluation
- Missing-field tracking + Next Best Action generation
- Mermaid state diagram export
- FastAPI API surface
"""

from .models import ReferralRecord, WorkflowPayload
from .workflow_router import WorkflowEngine

__all__ = ["ReferralRecord", "WorkflowPayload", "WorkflowEngine"]

