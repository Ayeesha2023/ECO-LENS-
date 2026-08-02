from datetime import date
from pprint import pprint

from services.analytics_service import (
    build_authority_analytics,
)
from services.rule_engine import (
    evaluate_authority_rules,
)


def main() -> None:
    authority_id = 1

    analytics = build_authority_analytics(
        authority_id=authority_id,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    print("\n========== ANALYTICS ==========")
    pprint(analytics)

    triggered_rules = evaluate_authority_rules(
        analytics
    )

    print("\n========== TRIGGERED RULES ==========")

    if not triggered_rules:
        print("No rules were triggered.")

    for rule in triggered_rules:
        pprint(rule)


if __name__ == "__main__":
    main()