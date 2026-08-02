from datetime import date
from pprint import pprint
from typing import Any

from db import fetch_one
from services.authority_rag_service import (
    generate_authority_advice_offline,
)


def _number(
    value: Any,
) -> int:
    """Safely convert a database number into an integer."""

    if value is None:
        return 0

    return int(value)


def main() -> None:
    """
    Test the complete Community Authority RAG pipeline.

    This test checks:
    1. Analytics generation
    2. Rule evaluation
    3. Verified knowledge retrieval
    4. Verified facility retrieval
    5. Offline recommendation creation
    6. Response validation
    7. Analytics snapshot storage
    8. Advice-run storage
    9. Rule-link storage
    10. Knowledge-link storage
    """

    authority_id = 1

    start_date = date(
        2026,
        1,
        1,
    )

    end_date = date(
        2026,
        12,
        31,
    )

    print("=" * 60)
    print("STARTING COMMUNITY AUTHORITY RAG TEST")
    print("=" * 60)

    result = generate_authority_advice_offline(
        authority_id=authority_id,
        start_date=start_date,
        end_date=end_date,
        response_language="en",
    )

    advice_run_id = int(
        result["advice_run_id"]
    )

    snapshot_id = int(
        result["snapshot_id"]
    )

    request_uuid = str(
        result["request_uuid"]
    )

    advice_result = result["result"]

    print("\n========== GENERATED IDENTIFIERS ==========")

    print(
        f"Advice Run ID: {advice_run_id}"
    )

    print(
        f"Snapshot ID: {snapshot_id}"
    )

    print(
        f"Request UUID: {request_uuid}"
    )

    print("\n========== RESPONSE MODE ==========")

    print(
        advice_result["mode"]
    )

    print("\n========== AUTHORITY SCOPE ==========")

    pprint(
        advice_result["scope"]
    )

    print("\n========== DATA QUALITY ==========")

    pprint(
        advice_result["data_quality"]
    )

    print("\n========== ANALYTICS SUMMARY ==========")

    for item in advice_result[
        "analytics_summary"
    ]:
        pprint(item)

    print("\n========== RECOMMENDATIONS ==========")

    recommendations = advice_result[
        "recommendations"
    ]

    if recommendations:
        for number, recommendation in enumerate(
            recommendations,
            start=1,
        ):
            print(
                f"\nRecommendation {number}"
            )

            pprint(
                recommendation
            )

    else:
        print(
            "No analytics rules were triggered."
        )

    print("\n========== VERIFIED SOURCES ==========")

    source_list = advice_result[
        "source_list"
    ]

    if source_list:
        for source in source_list:
            pprint(source)

    else:
        print(
            "No verified authority sources were retrieved."
        )

    print("\n========== VERIFIED FACILITIES ==========")

    verified_facilities = advice_result[
        "verified_facilities"
    ]

    if verified_facilities:
        for facility in verified_facilities:
            pprint(facility)

    else:
        print(
            "No verified facilities were found for this region."
        )

    print("\n========== DISCLAIMER ==========")

    print(
        advice_result["disclaimer"]
    )

    # ========================================================
    # VERIFY SAVED ADVICE RUN
    # ========================================================

    saved_advice_run = fetch_one(
        """
        SELECT
            advice_run_id,
            authority_id,
            region_id,
            snapshot_id,
            request_uuid,
            advice_status,
            gemini_model,
            prompt_version,
            response_language,
            executive_summary,
            recommendations_json,
            limitations_text,
            error_message,
            generated_at

        FROM authority_advice_runs

        WHERE advice_run_id = %s
        """,
        (advice_run_id,),
    )

    if saved_advice_run is None:
        raise RuntimeError(
            "The authority advice run was not saved."
        )

    print("\n========== SAVED ADVICE RUN ==========")

    pprint(
        saved_advice_run
    )

    # ========================================================
    # VERIFY SAVED SNAPSHOT
    # ========================================================

    saved_snapshot = fetch_one(
        """
        SELECT
            snapshot_id,
            authority_id,
            region_id,
            period_type,
            period_start,
            period_end,
            submitted_reports,
            unresolved_reports,
            completed_reports,
            total_waste_collected_kg,
            recycled_waste_kg,
            composted_waste_kg,
            hazardous_waste_kg,
            active_employee_count,
            completed_assignment_count,
            overdue_assignment_count,
            data_completeness_percent,
            calculated_at

        FROM authority_analytics_snapshots

        WHERE snapshot_id = %s
        """,
        (snapshot_id,),
    )

    if saved_snapshot is None:
        raise RuntimeError(
            "The analytics snapshot was not saved."
        )

    print("\n========== SAVED ANALYTICS SNAPSHOT ==========")

    pprint(
        saved_snapshot
    )

    # ========================================================
    # COUNT SAVED RULE LINKS
    # ========================================================

    saved_rule_count = fetch_one(
        """
        SELECT
            COUNT(*) AS total

        FROM authority_advice_rule_links

        WHERE advice_run_id = %s
        """,
        (advice_run_id,),
    )

    rule_link_count = _number(
        saved_rule_count.get("total")
        if saved_rule_count
        else 0
    )

    # ========================================================
    # COUNT SAVED KNOWLEDGE LINKS
    # ========================================================

    saved_knowledge_count = fetch_one(
        """
        SELECT
            COUNT(*) AS total

        FROM
            authority_advice_authority_knowledge_links

        WHERE advice_run_id = %s
        """,
        (advice_run_id,),
    )

    knowledge_link_count = _number(
        saved_knowledge_count.get("total")
        if saved_knowledge_count
        else 0
    )

    print("\n========== DATABASE AUDIT LINKS ==========")

    print(
        f"Saved rule links: {rule_link_count}"
    )

    print(
        "Saved authority knowledge links: "
        f"{knowledge_link_count}"
    )

    # ========================================================
    # FINAL VALIDATION
    # ========================================================

    if advice_result["mode"] != "offline_grounded":
        raise AssertionError(
            "The response mode should be offline_grounded."
        )

    if saved_advice_run["advice_status"] != (
        "needs_human_review"
    ):
        raise AssertionError(
            "The saved advice status should be "
            "needs_human_review."
        )

    if not saved_advice_run[
        "recommendations_json"
    ]:
        raise AssertionError(
            "The recommendation JSON was not saved."
        )

    if rule_link_count != len(
        recommendations
    ):
        raise AssertionError(
            "The number of saved rule links does not match "
            "the number of generated recommendations."
        )

    print("\n" + "=" * 60)
    print("COMMUNITY AUTHORITY RAG TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()