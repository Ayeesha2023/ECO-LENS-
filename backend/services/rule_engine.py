from decimal import Decimal
from typing import Any

from repositories.authority_repository import (
    get_active_advice_rules,
)


def _float(value: Any) -> float:
    if isinstance(value, Decimal):
        return float(value)

    return float(value or 0)


def _rule_matches(
    value: float,
    operator: str,
    threshold_1: float,
    threshold_2: float | None,
) -> bool:
    if operator == "gt":
        return value > threshold_1

    if operator == "gte":
        return value >= threshold_1

    if operator == "lt":
        return value < threshold_1

    if operator == "lte":
        return value <= threshold_1

    if operator == "eq":
        return value == threshold_1

    if operator == "between":
        if threshold_2 is None:
            return False

        return threshold_1 <= value <= threshold_2

    raise ValueError(f"Unsupported operator: {operator}")


def evaluate_authority_rules(
    analytics: dict[str, Any],
) -> list[dict[str, Any]]:
    """Evaluate transparent rules against calculated analytics."""

    rules = get_active_advice_rules()
    indicators = analytics["indicators"]

    total_reports = analytics["reports"]["submitted"]
    total_waste = analytics["waste"]["total_collected_kg"]
    active_assignments = analytics["assignments"]["active"]

    triggered: list[dict[str, Any]] = []

    for rule in rules:
        indicator_code = rule["indicator_code"]

        if indicator_code not in indicators:
            continue

        indicator_value = _float(
            indicators[indicator_code]
        )

        minimum_sample_size = int(
            rule["minimum_sample_size"] or 0
        )

        if "report" in indicator_code:
            sample_size = total_reports

        elif "assignment" in indicator_code:
            sample_size = active_assignments

        elif indicator_code == "data_completeness_percent":
            sample_size = 1

        else:
            sample_size = total_waste

        if sample_size < minimum_sample_size:
            continue

        threshold_1 = _float(
            rule["threshold_value_1"]
        )

        threshold_2_raw = rule["threshold_value_2"]

        threshold_2 = (
            _float(threshold_2_raw)
            if threshold_2_raw is not None
            else None
        )

        matches = _rule_matches(
            indicator_value,
            rule["comparison_operator"],
            threshold_1,
            threshold_2,
        )

        if not matches:
            continue

        triggered.append(
            {
                "advice_rule_id": rule["advice_rule_id"],
                "rule_code": rule["rule_code"],
                "title": rule["title"],
                "indicator_code": indicator_code,
                "trigger_value": indicator_value,
                "sample_size": sample_size,
                "priority": rule["priority"],
                "category": rule["advice_category"],
                "recommendation": (
                    rule["recommendation_template"]
                ),
                "rationale": rule["rationale_template"],
                "human_review_required": bool(
                    rule["requires_human_review"]
                ),
            }
        )

    return triggered