from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from .models import ReferralState, RuleDefinition, RuleSet


class RuleEngineError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class LoadedRules:
    """Rules loaded from JSON, keyed by state name."""

    by_state: Dict[ReferralState, RuleSet]


class ReferralRuleEngine:
    """
    JSON-configured rule engine for referrals.

    - Loads per-state rule sets from JSON.
    - Evaluates conditions against a referral's attributes using a safe AST evaluator.
    """

    def __init__(self, rules_path: Path) -> None:
        self._rules_path = rules_path
        self._loaded: Optional[LoadedRules] = None

    def load(self) -> LoadedRules:
        raw = json.loads(self._rules_path.read_text(encoding="utf-8"))
        by_state: Dict[ReferralState, RuleSet] = {}

        for state, spec in raw.items():
            rules = [RuleDefinition(**r) for r in spec.get("rules", [])]
            by_state[state] = RuleSet(
                rules=rules,
                success_state=spec["success_state"],
                failure_state=spec["failure_state"],
            )

        self._loaded = LoadedRules(by_state=by_state)
        return self._loaded

    def rules_for_state(self, state: ReferralState) -> Optional[RuleSet]:
        if self._loaded is None:
            self.load()
        return self._loaded.by_state.get(state) if self._loaded else None

    def evaluate_condition(self, condition: str, attributes: Mapping[str, Any]) -> bool:
        """
        Evaluate a condition string safely.

        Supported:
        - `null` literal (mapped to None)
        - boolean operators: and/or/not
        - comparisons: ==, !=, <, <=, >, >=, in, not in, is, is not
        - parentheses, string/number/bool literals
        - attribute references as identifiers (e.g. `patient_name`)
        """

        expr = _preprocess_condition(condition)
        try:
            tree = ast.parse(expr, mode="eval")
        except SyntaxError as e:
            raise RuleEngineError(f"Invalid condition syntax: {condition}") from e

        evaluator = _SafeEvaluator(attributes)
        result = evaluator.eval(tree.body)
        if not isinstance(result, bool):
            raise RuleEngineError(f"Condition did not evaluate to bool: {condition}")
        return result

    def referenced_fields(self, condition: str) -> Set[str]:
        """Return identifiers referenced by a condition (best-effort)."""

        expr = _preprocess_condition(condition)
        try:
            tree = ast.parse(expr, mode="eval")
        except SyntaxError:
            return set()

        names: Set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                if node.id not in {"None", "True", "False"}:
                    names.add(node.id)
        return names


def _preprocess_condition(condition: str) -> str:
    # JSON uses `null`; Python uses `None`.
    return condition.replace("null", "None")


class _SafeEvaluator:
    """
    Minimal safe expression evaluator for boolean conditions.

    This is intentionally limited to avoid arbitrary code execution.
    """

    __slots__ = ("_attrs",)

    def __init__(self, attrs: Mapping[str, Any]) -> None:
        self._attrs = attrs

    def eval(self, node: ast.AST) -> Any:
        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                return all(self.eval(v) for v in node.values)
            if isinstance(node.op, ast.Or):
                return any(self.eval(v) for v in node.values)
            raise RuleEngineError("Unsupported boolean operator")

        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not bool(self.eval(node.operand))

        if isinstance(node, ast.Compare):
            left = self.eval(node.left)
            for op, comparator in zip(node.ops, node.comparators, strict=False):
                right = self.eval(comparator)
                if not _compare(left, op, right):
                    return False
                left = right
            return True

        if isinstance(node, ast.Name):
            if node.id in {"None", "True", "False"}:
                return {"None": None, "True": True, "False": False}[node.id]
            return self._attrs.get(node.id)

        if isinstance(node, ast.Constant):
            return node.value

        if isinstance(node, ast.Expr):
            return self.eval(node.value)

        if isinstance(node, ast.BinOp):
            # Allow simple string concatenation in future, but disallow now.
            raise RuleEngineError("Binary operations not supported")

        if isinstance(node, ast.Call):
            raise RuleEngineError("Function calls not supported")

        if isinstance(node, ast.Attribute):
            raise RuleEngineError("Attribute access not supported")

        if isinstance(node, ast.Subscript):
            raise RuleEngineError("Subscript access not supported")

        raise RuleEngineError(f"Unsupported expression node: {type(node).__name__}")


def _compare(left: Any, op: ast.cmpop, right: Any) -> bool:
    if isinstance(op, ast.Eq):
        return left == right
    if isinstance(op, ast.NotEq):
        return left != right
    if isinstance(op, ast.Lt):
        return left < right
    if isinstance(op, ast.LtE):
        return left <= right
    if isinstance(op, ast.Gt):
        return left > right
    if isinstance(op, ast.GtE):
        return left >= right
    if isinstance(op, ast.In):
        return left in right
    if isinstance(op, ast.NotIn):
        return left not in right
    if isinstance(op, ast.Is):
        return left is right
    if isinstance(op, ast.IsNot):
        return left is not right
    raise RuleEngineError(f"Unsupported comparison operator: {type(op).__name__}")

