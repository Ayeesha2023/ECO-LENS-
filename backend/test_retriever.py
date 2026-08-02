from datetime import date
from pprint import pprint

from services.analytics_service import (
    build_authority_analytics,
)
from services.authority_retriever import (
    get_topics_for_rules,
    retrieve_verified_authority_knowledge,
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

    triggered_rules = evaluate_authority_rules(analytics)

    topics = get_topics_for_rules(triggered_rules)

    knowledge = retrieve_verified_authority_knowledge(
        region_id=analytics["scope"]["region_id"],
        triggered_rules=triggered_rules,
    )

    print("\n========== TRIGGERED RULES ==========")
    pprint(triggered_rules)

    print("\n========== RETRIEVAL TOPICS ==========")
    pprint(topics)

    print("\n========== VERIFIED KNOWLEDGE ==========")

    if not knowledge:
        print(
            "No verified authority knowledge exists yet. "
            "This is expected until official source passages "
            "are reviewed and inserted."
        )
    else:
        pprint(knowledge)


if __name__ == "__main__":
    main()