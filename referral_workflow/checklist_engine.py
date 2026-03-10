from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Mapping

from .models import ChecklistItem, RuleEvaluation, RuleSet
from .rule_engine import ReferralRuleEngine


@dataclass(slots=True)
class ChecklistEngine:
    """
    Evaluates a `RuleSet` against referral attributes and returns checklist + missing fields.
    """

    rule_engine: ReferralRuleEngine

    def evaluate(self, rule_set: RuleSet, attributes: Mapping[str, Any]) -> RuleEvaluation:
        checklist: List[ChecklistItem] = []
        failed_rule_names: List[str] = []
        missing_fields: List[str] = []

        for rule in rule_set.rules:
            passed = self.rule_engine.evaluate_condition(rule.condition, attributes)
            checklist.append(ChecklistItem(rule=rule.name, status="passed" if passed else "failed"))
            if not passed:
                failed_rule_names.append(rule.name)
                missing_fields.extend(self._missing_fields_for_rule(rule.condition, attributes))

        # De-dupe but preserve order.
        missing_fields = list(dict.fromkeys(missing_fields))

        return RuleEvaluation(
            checklist=checklist,
            passed=all(item.status == "passed" for item in checklist),
            failed_rule_names=failed_rule_names,
            missing_fields=missing_fields,
            success_state=rule_set.success_state,
            failure_state=rule_set.failure_state,
        )

    def _missing_fields_for_rule(self, condition: str, attributes: Mapping[str, Any]) -> List[str]:
        """
        Best-effort missing-field detection.

        If a rule fails, we consider referenced fields "missing" when their value is:
        - None
        - empty string after stripping
        - empty list/dict/tuple/set
        """

        fields = sorted(self.rule_engine.referenced_fields(condition))
        missing: List[str] = []
        for f in fields:
            v = attributes.get(f)
            if v is None:
                missing.append(f)
            elif isinstance(v, str) and v.strip() == "":
                missing.append(f)
            elif isinstance(v, (list, dict, tuple, set)) and len(v) == 0:
                missing.append(f)
        return missing

