from typing import Any

from db import fetch_all


RULE_TOPIC_MAP: dict[str, list[str]] = {
    "HIGH_UNRESOLVED_REPORT_RATE": [
        "complaint_management",
        "collection_operations",
        "staffing",
    ],
    "HIGH_OVERDUE_ASSIGNMENT_RATE": [
        "staffing",
        "route_planning",
        "collection_operations",
    ],
    "LOW_RECYCLING_SHARE": [
        "recycling",
        "collection_operations",
        "citizen_engagement",
    ],
    "HIGH_ORGANIC_SHARE": [
        "composting",
        "collection_operations",
        "infrastructure",
    ],
    "HIGH_HAZARDOUS_SHARE": [
        "hazardous_waste",
        "ewaste",
        "worker_safety",
    ],
    "INSUFFICIENT_ANALYTICS_DATA": [
        "data_quality",
        "environmental_reporting",
    ],
}


def get_topics_for_rules(
    triggered_rules: list[dict[str, Any]],
) -> list[str]:
    """Map triggered analytics rules to authority knowledge topics."""

    topics: set[str] = set()

    for rule in triggered_rules:
        rule_code = rule["rule_code"]

        for topic in RULE_TOPIC_MAP.get(rule_code, []):
            topics.add(topic)

    return sorted(topics)


def retrieve_verified_authority_knowledge(
    region_id: int,
    triggered_rules: list[dict[str, Any]],
    limit: int = 12,
) -> list[dict[str, Any]]:
    """
    Retrieve only verified authority-level Bangladesh knowledge.

    Retrieval order:
    1. Exact region and matching topic
    2. National Bangladesh matching topic
    """

    topics = get_topics_for_rules(triggered_rules)

    if not topics:
        return []

    placeholders = ", ".join(["%s"] * len(topics))

    query = f"""
        SELECT
            authority_knowledge_id,
            region_id,
            topic_code,
            title,
            supported_statement,
            recommended_application,
            applicability_conditions,
            limitations_text,

            source_id,
            source_title,
            issuing_authority,
            jurisdiction_level,
            jurisdiction_name,
            source_url,
            official_domain,
            document_version,

            source_page_start,
            source_page_end,
            source_section,
            source_excerpt,

            last_source_check_at,
            source_last_checked_at,
            priority

        FROM v_verified_authority_rag_knowledge

        WHERE topic_code IN ({placeholders})
          AND (
              region_id = %s
              OR region_id IS NULL
          )

        ORDER BY
            CASE
                WHEN region_id = %s THEN 1
                ELSE 2
            END,
            priority DESC,
            authority_knowledge_id ASC

        LIMIT %s
    """

    params: tuple[Any, ...] = (
        *topics,
        region_id,
        region_id,
        limit,
    )

    return fetch_all(query, params)