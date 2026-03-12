from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, FastAPI, HTTPException

from .models import ActionRequest, MermaidResponse, MermaidUpdateRequest, ReferralRecord, WorkflowPayload
from .state_machine import InvalidActionError, ReferralStateMachine
from .workflow_router import WorkflowEngine


@dataclass(slots=True)
class ReferralRepository:
    """
    Minimal repository abstraction.

    Replace with a DB-backed implementation (SQLAlchemy, Django ORM, etc.).
    """

    _store: Dict[str, ReferralRecord]

    def get(self, referral_id: str) -> Optional[ReferralRecord]:
        return self._store.get(referral_id)

    def upsert(self, record: ReferralRecord) -> None:
        self._store[record.referral_id] = record


def create_app(
    *,
    rules_path: Path | None = None,
    repository: ReferralRepository | None = None,
) -> FastAPI:
    """
    Create a FastAPI app that exposes workflow endpoints.

    - `rules_path`: path to `rules/referral_rules.json` (defaults to repo-local).
    - `repository`: referral persistence abstraction (defaults to in-memory).
    """

    base_dir = Path(__file__).resolve().parents[1]  # D:\NBA\
    resolved_rules_path = rules_path or (base_dir / "rules" / "referral_rules.json")
    engine = WorkflowEngine(rules_path=resolved_rules_path)

    repo = repository or ReferralRepository(
        _store={
            # Patient 123: All details complete → completed.
            "123": ReferralRecord(
                referral_id="123",
                state="completed",
                attributes={
                    "patient_name": "Margaret Thompson",
                    "insurance": "Cigna",
                    "contact_number": "555-0201",
                },
            ),
            # Patient 456: Needs review.
            "456": ReferralRecord(
                referral_id="456",
                state="needs_review",
                attributes={
                    "patient_name": "Robert Garcia",
                    "insurance": None,
                    "contact_number": None,
                },
            ),
            # Patient 789: Rejected.
            "789": ReferralRecord(
                referral_id="789",
                state="rejected",
                attributes={
                    "patient_name": "Linda Chen",
                    "insurance": "Aetna",
                    "contact_number": "555-0302",
                },
            ),
            # Patient 101: Needs review, all fields present.
            "101": ReferralRecord(
                referral_id="101",
                state="needs_review",
                attributes={
                    "patient_name": "James Williams",
                    "insurance": "Medicare",
                    "contact_number": "555-0403",
                },
            ),
            # Patient 202: Just received, minimal info.
            "202": ReferralRecord(
                referral_id="202",
                state="referral_received",
                attributes={
                    "patient_name": "Susan Martinez",
                },
            ),
            # Patient 303: Incomplete.
            "303": ReferralRecord(
                referral_id="303",
                state="incomplete",
                attributes={
                    "patient_name": "John Doe",
                    "insurance": None,
                    "contact_number": None,
                },
            ),
        }
    )

    router = APIRouter(prefix="/referral", tags=["referral-workflow"])

    def _load_or_404(referral_id: str) -> ReferralRecord:
        record = repo.get(referral_id)
        if not record:
            raise HTTPException(status_code=404, detail="Referral not found")
        return record

    def _build_machine(record: ReferralRecord) -> ReferralStateMachine:
        def _on_change(r: ReferralRecord):
            decision = engine.evaluate(r)
            return decision.next_state

        return ReferralStateMachine(record=record, on_state_change=_on_change)

    @router.get("/{referral_id}/workflow", response_model=WorkflowPayload)
    def get_workflow(referral_id: str) -> WorkflowPayload:
        record = _load_or_404(referral_id)
        machine = _build_machine(record)

        # Ensure state is correct based on current attributes (auto-route).
        machine.apply_routing()
        repo.upsert(record)

        return engine.payload(record, machine)

    @router.get("/{referral_id}/mermaid", response_model=MermaidResponse)
    def get_mermaid(referral_id: str) -> MermaidResponse:
        record = _load_or_404(referral_id)

        # If a custom (user-edited) diagram was saved, return it directly.
        if record.custom_mermaid_diagram:
            return MermaidResponse(diagram=record.custom_mermaid_diagram)

        # Otherwise, generate from the engine.
        machine = _build_machine(record)
        machine.apply_routing()
        repo.upsert(record)
        payload = engine.payload(record, machine)
        return MermaidResponse(diagram=payload.mermaid_diagram)

    @router.put("/{referral_id}/mermaid")
    def update_mermaid(referral_id: str, req: MermaidUpdateRequest) -> Dict[str, Any]:
        """Save a custom Mermaid diagram for a patient. Overrides the generated one."""
        record = _load_or_404(referral_id)
        if not req.diagram or not req.diagram.strip():
            raise HTTPException(status_code=400, detail="Diagram cannot be empty")

        record.custom_mermaid_diagram = req.diagram
        repo.upsert(record)
        return {"referral_id": referral_id, "saved": True}

    @router.post("/{referral_id}/action", response_model=WorkflowPayload)
    def execute_action(referral_id: str, req: ActionRequest) -> WorkflowPayload:
        record = _load_or_404(referral_id)
        machine = _build_machine(record)

        # Demo-friendly: allow actions to optionally carry attribute updates.
        # Example: { "action": "submit_insurance", "data": { "insurance": "Aetna PPO" } }
        if req.data:
            record.attributes.update(req.data)

        # Demo-friendly: a few "autofill" actions that set common missing fields.
        # This avoids requiring the client to send `data` for every click.
        if req.action == "provide_insurance" and not record.attributes.get("insurance"):
            record.attributes["insurance"] = "Demo Insurance"
        elif req.action == "provide_contact_number" and not record.attributes.get("contact_number"):
            record.attributes["contact_number"] = "555-0100"
        elif req.action == "provide_patient_name" and not record.attributes.get("patient_name"):
            record.attributes["patient_name"] = "Demo Patient"

        try:
            machine.execute_action(req.action)
        except InvalidActionError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

        # After any action, re-route based on current state/attributes.
        machine.apply_routing()
        repo.upsert(record)

        return engine.payload(record, machine)

    app = FastAPI(title="Hospice Referral Workflow API", version="1.0.0")
    app.include_router(router)
    return app


app = create_app()

