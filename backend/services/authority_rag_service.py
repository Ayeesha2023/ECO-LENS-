from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from repositories.authority_repository import (
    complete_authority_advice_run,
    create_authority_advice_run,
    fail_authority_advice_run,
    get_verified_facilities,
    save_analytics_snapshot,
    save_authority_knowledge_links,
    save_authority_rule_links,
)
from schemas.authority_advice_schema import (
    AuthorityAdviceResponse,
    validate_authority_advice_response,
)
from services.analytics_service import (
    build_authority_analytics,
)
from services.authority_retriever import (
    RULE_TOPIC_MAP,
    retrieve_verified_authority_knowledge,
)
from services.rule_engine import (
    evaluate_authority_rules,
)


# ============================================================
# GENERAL HELPERS
# ============================================================

def _date_to_text(
    value: Any,
) -> str | None:
    """Convert database date values into text."""

    if value is None:
        return None

    if isinstance(value, (date, datetime)):
        return value.isoformat()

    return str(value)


def _json_safe_value(
    value: Any,
) -> Any:
    """
    Convert MySQL-specific values into JSON-safe values.

    This is mainly used for verified disposal facilities,
    which may contain Decimal, date or datetime values.
    """

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, (date, datetime)):
        return value.isoformat()

    if isinstance(value, dict):
        return {
            key: _json_safe_value(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            _json_safe_value(item)
            for item in value
        ]

    return value


def _remove_duplicate_text(
    items: list[str],
) -> list[str]:
    """Remove repeated text while preserving the original order."""

    result: list[str] = []
    seen: set[str] = set()

    for item in items:
        cleaned_item = item.strip()

        if not cleaned_item:
            continue

        if cleaned_item in seen:
            continue

        seen.add(cleaned_item)
        result.append(cleaned_item)

    return result


def _source_page_or_section(
    knowledge: dict[str, Any],
) -> str:
    """
    Return the most specific source location available.

    Preference:
    1. Source section
    2. Page range
    3. Single page
    4. Not recorded
    """

    section = knowledge.get("source_section")

    if section:
        return str(section)

    start_page = knowledge.get(
        "source_page_start"
    )

    end_page = knowledge.get(
        "source_page_end"
    )

    if (
        start_page is not None
        and end_page is not None
    ):
        if start_page == end_page:
            return f"Page {start_page}"

        return f"Pages {start_page}-{end_page}"

    if start_page is not None:
        return f"Page {start_page}"

    return "Not recorded"


# ============================================================
# ANALYTICS SUMMARY
# ============================================================

def _build_analytics_summary(
    analytics: dict[str, Any],
) -> list[dict[str, Any]]:
    """Create a clear analytics summary for the authority."""

    reports = analytics["reports"]
    assignments = analytics["assignments"]
    waste = analytics["waste"]
    indicators = analytics["indicators"]

    return [
        {
            "indicator": "Total reports",
            "value": float(
                reports["submitted"]
            ),
            "unit": "reports",
            "meaning": (
                "Citizen waste reports received during "
                "the selected reporting period."
            ),
        },
        {
            "indicator": "Unresolved reports",
            "value": float(
                reports["unresolved"]
            ),
            "unit": "reports",
            "meaning": (
                "Reports that are submitted, under review, "
                "assigned or still in progress."
            ),
        },
        {
            "indicator": "Report completion rate",
            "value": float(
                indicators[
                    "report_completion_rate_percent"
                ]
            ),
            "unit": "percent",
            "meaning": (
                "The percentage of submitted reports marked "
                "as completed."
            ),
        },
        {
            "indicator": "Unresolved report rate",
            "value": float(
                indicators[
                    "unresolved_report_rate_percent"
                ]
            ),
            "unit": "percent",
            "meaning": (
                "The percentage of submitted reports that "
                "remain unresolved."
            ),
        },
        {
            "indicator": "Total waste collected",
            "value": float(
                waste["total_collected_kg"]
            ),
            "unit": "kg",
            "meaning": (
                "Waste recorded in authority-verified "
                "cleanup records."
            ),
        },
        {
            "indicator": "Recycling share",
            "value": float(
                indicators[
                    "recycling_share_percent"
                ]
            ),
            "unit": "percent",
            "meaning": (
                "The percentage of collected waste recorded "
                "as recycled."
            ),
        },
        {
            "indicator": "Composted share",
            "value": float(
                indicators[
                    "compostable_share_percent"
                ]
            ),
            "unit": "percent",
            "meaning": (
                "The percentage of collected waste recorded "
                "as composted."
            ),
        },
        {
            "indicator": "Hazardous-waste share",
            "value": float(
                indicators[
                    "hazardous_share_percent"
                ]
            ),
            "unit": "percent",
            "meaning": (
                "The percentage of collected waste recorded "
                "as hazardous."
            ),
        },
        {
            "indicator": "Active assignments",
            "value": float(
                assignments["active"]
            ),
            "unit": "assignments",
            "meaning": (
                "Cleaning assignments that are assigned, "
                "accepted or in progress."
            ),
        },
        {
            "indicator": "Overdue assignments",
            "value": float(
                assignments["overdue"]
            ),
            "unit": "assignments",
            "meaning": (
                "Active assignments whose due dates have "
                "already passed."
            ),
        },
        {
            "indicator": "Active employees",
            "value": float(
                assignments["active_employees"]
            ),
            "unit": "employees",
            "meaning": (
                "Active cleaning employees registered under "
                "the authority."
            ),
        },
    ]


# ============================================================
# VERIFIED SOURCE LIST
# ============================================================

def _build_source_list(
    knowledge_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Build a unique list of official sources used by retrieval.

    Multiple knowledge records may come from the same source,
    so duplicate source IDs are removed.
    """

    sources_by_id: dict[int, dict[str, Any]] = {}

    for knowledge in knowledge_rows:
        source_id_value = knowledge.get("source_id")

        if source_id_value is None:
            continue

        source_id = int(source_id_value)

        if source_id in sources_by_id:
            continue

        jurisdiction_level = (
            knowledge.get("jurisdiction_level")
            or "not_recorded"
        )

        jurisdiction_name = (
            knowledge.get("jurisdiction_name")
            or "Not recorded"
        )

        sources_by_id[source_id] = {
            "source_id": source_id,
            "title": (
                knowledge.get("source_title")
                or "Untitled official source"
            ),
            "issuing_authority": (
                knowledge.get("issuing_authority")
                or "Not recorded"
            ),
            "jurisdiction": (
                f"{jurisdiction_level}: "
                f"{jurisdiction_name}"
            ),
            "page_or_section": (
                _source_page_or_section(
                    knowledge
                )
            ),
            "last_checked_at": (
                _date_to_text(
                    knowledge.get(
                        "source_last_checked_at"
                    )
                )
            ),
            "source_url": knowledge.get(
                "source_url"
            ),
        }

    return list(sources_by_id.values())


# ============================================================
# RECOMMENDATION BUILDING
# ============================================================

def _get_rule_topics(
    rule_code: str,
) -> set[str]:
    """Return retrieval topics connected to one rule."""

    topics = RULE_TOPIC_MAP.get(
        rule_code,
        [],
    )

    return set(topics)


def _find_matching_knowledge(
    rule: dict[str, Any],
    knowledge_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Find verified knowledge relevant to a triggered rule."""

    rule_topics = _get_rule_topics(
        rule["rule_code"]
    )

    if not rule_topics:
        return []

    return [
        knowledge
        for knowledge in knowledge_rows
        if knowledge.get("topic_code") in rule_topics
    ]


def _build_recommendations(
    triggered_rules: list[dict[str, Any]],
    knowledge_rows: list[dict[str, Any]],
    limitations: list[str],
) -> list[dict[str, Any]]:
    """
    Build deterministic recommendations without Gemini.

    Each recommendation begins with an ECO-LENS analytics rule.
    Verified authority knowledge is added only when retrieved.
    """

    recommendations: list[dict[str, Any]] = []

    for rule in triggered_rules:
        matching_knowledge = (
            _find_matching_knowledge(
                rule=rule,
                knowledge_rows=knowledge_rows,
            )
        )

        actions: list[str] = [
            str(rule["recommendation"])
        ]

        source_ids: list[int] = []

        for knowledge in matching_knowledge:
            recommended_application = (
                knowledge.get(
                    "recommended_application"
                )
            )

            if recommended_application:
                actions.append(
                    str(recommended_application)
                )

            source_id_value = knowledge.get(
                "source_id"
            )

            if source_id_value is not None:
                source_id = int(
                    source_id_value
                )

                if source_id not in source_ids:
                    source_ids.append(
                        source_id
                    )

        actions = _remove_duplicate_text(
            actions
        )

        why = (
            f"{rule['rationale']} "
            f"The calculated value of "
            f"{rule['indicator_code']} was "
            f"{rule['trigger_value']}."
        )

        if matching_knowledge:
            why += (
                " Verified authority knowledge was retrieved "
                "for this recommendation."
            )

        else:
            why += (
                " No verified authority knowledge was "
                "available for this topic."
            )

            limitations.append(
                (
                    "No verified Community Authority "
                    "knowledge supported rule "
                    f"{rule['rule_code']}. Its recommendation "
                    "is based only on the transparent "
                    "ECO-LENS analytics rule."
                )
            )

        recommendations.append(
            {
                "priority": rule["priority"],
                "category": rule["category"],
                "title": rule["title"],
                "why": why,
                "actions": actions,
                "indicators_used": [
                    rule["indicator_code"]
                ],
                "source_ids": source_ids,
                "human_review_required": bool(
                    rule[
                        "human_review_required"
                    ]
                ),
            }
        )

    return recommendations


# ============================================================
# EXECUTIVE SUMMARY
# ============================================================

def _build_executive_summary(
    analytics: dict[str, Any],
    triggered_rules: list[dict[str, Any]],
    knowledge_rows: list[dict[str, Any]],
) -> str:
    """Create a short summary for advice history."""

    region_name = analytics["scope"][
        "region_name"
    ]

    rule_count = len(
        triggered_rules
    )

    knowledge_count = len(
        knowledge_rows
    )

    if rule_count == 0:
        return (
            f"No configured analytics conditions were "
            f"triggered for {region_name}."
        )

    return (
        f"{rule_count} analytics condition(s) were "
        f"identified for {region_name}. "
        f"{knowledge_count} verified authority knowledge "
        f"record(s) were retrieved."
    )


# ============================================================
# COMPLETE OFFLINE AUTHORITY RAG PIPELINE
# ============================================================

def generate_authority_advice_offline(
    authority_id: int,
    start_date: date,
    end_date: date,
    response_language: str = "en",
) -> dict[str, Any]:
    """
    Run the complete Community Authority RAG pipeline
    without Gemini.

    Pipeline:
    1. Build authority analytics.
    2. Evaluate transparent rules.
    3. Retrieve verified authority knowledge.
    4. Retrieve verified disposal facilities.
    5. Build deterministic grounded recommendations.
    6. Validate the response structure.
    7. Save the analytics snapshot.
    8. Save the advice run and audit links.
    """

    if response_language not in {
        "en",
        "bn",
    }:
        raise ValueError(
            "response_language must be 'en' or 'bn'."
        )

    advice_run_id: int | None = None

    try:
        # ----------------------------------------------------
        # 1. Build analytics
        # ----------------------------------------------------

        analytics = build_authority_analytics(
            authority_id=authority_id,
            start_date=start_date,
            end_date=end_date,
        )

        scope = analytics["scope"]

        # ----------------------------------------------------
        # 2. Trigger transparent rules
        # ----------------------------------------------------

        triggered_rules = (
            evaluate_authority_rules(
                analytics
            )
        )

        # ----------------------------------------------------
        # 3. Retrieve verified authority knowledge
        # ----------------------------------------------------

        knowledge_rows = (
            retrieve_verified_authority_knowledge(
                region_id=scope["region_id"],
                triggered_rules=triggered_rules,
            )
        )

        # ----------------------------------------------------
        # 4. Retrieve verified facilities
        # ----------------------------------------------------

        verified_facilities = (
            get_verified_facilities(
                region_id=scope["region_id"]
            )
        )

        verified_facilities = (
            _json_safe_value(
                verified_facilities
            )
        )

        # ----------------------------------------------------
        # 5. Save analytics snapshot
        # ----------------------------------------------------

        snapshot_id = save_analytics_snapshot(
            analytics=analytics,
            period_type="custom",
        )

        # ----------------------------------------------------
        # 6. Create advice run
        # ----------------------------------------------------

        request_uuid = str(
            uuid4()
        )

        advice_run_id = (
            create_authority_advice_run(
                authority_id=authority_id,
                region_id=scope["region_id"],
                snapshot_id=snapshot_id,
                request_uuid=request_uuid,
                requested_by_user_id=(
                    scope[
                        "authority_user_id"
                    ]
                ),
                response_language=(
                    response_language
                ),
            )
        )

        # ----------------------------------------------------
        # 7. Prepare limitations
        # ----------------------------------------------------

        limitations: list[str] = [
            (
                "Gemini was not used. The response was "
                "created from transparent analytics rules "
                "and verified database retrieval."
            )
        ]

        completeness_percent = float(
            analytics["data_quality"][
                "completeness_percent"
            ]
        )

        if completeness_percent < 80:
            limitations.append(
                (
                    "Data completeness is below 80 percent. "
                    "All recommendations must be treated "
                    "as provisional."
                )
            )

        if not knowledge_rows:
            limitations.append(
                (
                    "No verified Community Authority "
                    "knowledge records matched the "
                    "detected topics."
                )
            )

        if not verified_facilities:
            limitations.append(
                (
                    "No verified disposal or recovery "
                    "facility was available for this region."
                )
            )

        # ----------------------------------------------------
        # 8. Build recommendations
        # ----------------------------------------------------

        recommendations = (
            _build_recommendations(
                triggered_rules=triggered_rules,
                knowledge_rows=knowledge_rows,
                limitations=limitations,
            )
        )

        limitations = (
            _remove_duplicate_text(
                limitations
            )
        )

        # ----------------------------------------------------
        # 9. Build final response
        # ----------------------------------------------------

        response: AuthorityAdviceResponse = {
            "mode": "offline_grounded",
            "scope": {
                "authority_id": int(
                    scope["authority_id"]
                ),
                "authority_name": str(
                    scope["authority_name"]
                ),
                "organization_name": (
                    scope.get(
                        "organization_name"
                    )
                ),
                "region_id": int(
                    scope["region_id"]
                ),
                "region_name": str(
                    scope["region_name"]
                ),
                "region_type": str(
                    scope["region_type"]
                ),
                "period_start": str(
                    scope["period_start"]
                ),
                "period_end": str(
                    scope["period_end"]
                ),
            },
            "data_quality": {
                "status": analytics[
                    "data_quality"
                ]["status"],
                "completeness_percent": (
                    completeness_percent
                ),
                "limitations": limitations,
            },
            "analytics_summary": (
                _build_analytics_summary(
                    analytics
                )
            ),
            "recommendations": recommendations,
            "source_list": (
                _build_source_list(
                    knowledge_rows
                )
            ),
            "verified_facilities": (
                verified_facilities
            ),
            "disclaimer": (
                "This is decision-support information for "
                "human review. It is not a substitute for "
                "official instructions, legal advice or "
                "professional engineering assessment."
            ),
        }

        # ----------------------------------------------------
        # 10. Validate response
        # ----------------------------------------------------

        validated_response = (
            validate_authority_advice_response(
                response
            )
        )

        # ----------------------------------------------------
        # 11. Save rule links
        # ----------------------------------------------------

        save_authority_rule_links(
            advice_run_id=advice_run_id,
            triggered_rules=triggered_rules,
        )

        # ----------------------------------------------------
        # 12. Save knowledge links
        # ----------------------------------------------------

        save_authority_knowledge_links(
            advice_run_id=advice_run_id,
            knowledge_rows=knowledge_rows,
            exact_region_id=scope["region_id"],
        )

        # ----------------------------------------------------
        # 13. Complete advice run
        # ----------------------------------------------------

        executive_summary = (
            _build_executive_summary(
                analytics=analytics,
                triggered_rules=triggered_rules,
                knowledge_rows=knowledge_rows,
            )
        )

        complete_authority_advice_run(
            advice_run_id=advice_run_id,
            executive_summary=executive_summary,
            advice_response=validated_response,
            limitations=limitations,
        )

        # ----------------------------------------------------
        # 14. Return result
        # ----------------------------------------------------

        return {
            "advice_run_id": advice_run_id,
            "snapshot_id": snapshot_id,
            "request_uuid": request_uuid,
            "result": validated_response,
        }

    except Exception as exc:
        if advice_run_id is not None:
            fail_authority_advice_run(
                advice_run_id=advice_run_id,
                error_message=str(exc),
            )

        raise