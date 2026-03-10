from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple

from .checklist_engine import ChecklistEngine
from .mermaid_generator import MermaidGenerator
from .models import ReferralRecord, ReferralState, RuleEvaluation, WorkflowPayload
from .nba_engine import NextBestActionEngine
from .rule_engine import ReferralRuleEngine
from .state_machine import ReferralStateMachine


@dataclass(slots=True)
class WorkflowDecision:
    next_state: Optional[ReferralState]
    evaluation: Optional[RuleEvaluation]


@dataclass(slots=True)
class WorkflowEngine:
    """
    High-level workflow orchestrator.

    Responsibilities:
    - Evaluate rules for the current state
    - Compute missing fields and NBA suggestions
    - Decide the next state based on configured success/failure states
    - Produce the final payload (including Mermaid diagram)
    """

    rules_path: Path
    rule_engine: ReferralRuleEngine = field(init=False)
    checklist_engine: ChecklistEngine = field(init=False)
    nba_engine: NextBestActionEngine = field(init=False)
    mermaid: MermaidGenerator = field(init=False)

    def __post_init__(self) -> None:
        self.rule_engine = ReferralRuleEngine(self.rules_path)
        self.checklist_engine = ChecklistEngine(self.rule_engine)
        self.nba_engine = NextBestActionEngine.default()
        self.mermaid = MermaidGenerator()

    def evaluate(self, record: ReferralRecord) -> WorkflowDecision:
        rule_set = self.rule_engine.rules_for_state(record.state)
        if not rule_set:
            return WorkflowDecision(next_state=None, evaluation=None)

        evaluation = self.checklist_engine.evaluate(rule_set, record.attributes)
        next_state: ReferralState = rule_set.success_state if evaluation.passed else rule_set.failure_state
        return WorkflowDecision(next_state=next_state, evaluation=evaluation)

    def payload(self, record: ReferralRecord, machine: ReferralStateMachine) -> WorkflowPayload:
        decision = self.evaluate(record)

        missing_fields = decision.evaluation.missing_fields if decision.evaluation else []
        checklist = decision.evaluation.checklist if decision.evaluation else []
        nbas = self.nba_engine.generate(missing_fields)

        if record.custom_mermaid_diagram:
            diagram = record.custom_mermaid_diagram
        else:
            diagram = self.mermaid.generate(machine.transitions, current_state=record.state)

        return WorkflowPayload(
            current_state=record.state,
            attributes=dict(record.attributes),
            missing_fields=missing_fields,
            checklist=checklist,
            next_best_actions=nbas,
            mermaid_diagram=diagram,
        )

