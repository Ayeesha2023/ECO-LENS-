from pprint import pprint
from typing import Any
from uuid import uuid4

from db import execute, fetch_one
from services.household_rag_service import (
    generate_household_advice_offline,
)


# ============================================================
# SMALL HELPERS
# ============================================================

def _to_int(
    value: Any,
) -> int:
    """Convert a database number into an integer."""

    if value is None:
        return 0

    return int(value)


# ============================================================
# FIND REQUIRED DEMO RECORDS
# ============================================================

def _get_demo_household_user() -> dict[str, Any]:
    """Find an active household user for testing."""

    user = fetch_one(
        """
        SELECT
            user_id,
            full_name,
            email,
            region_id

        FROM users

        WHERE role = 'household'
          AND account_status = 'active'

        ORDER BY user_id

        LIMIT 1
        """
    )

    if user is None:
        raise RuntimeError(
            "No active household user was found. "
            "Create the demo household user first."
        )

    return user


def _get_current_model() -> dict[str, Any]:
    """Find the currently deployed YOLO model."""

    model = fetch_one(
        """
        SELECT
            model_version_id,
            version_name,
            architecture,
            global_confidence_threshold

        FROM model_versions

        WHERE is_current_deployment = 1
          AND artifact_status = 'available'

        ORDER BY model_version_id DESC

        LIMIT 1
        """
    )

    if model is None:
        raise RuntimeError(
            "No current deployable model version was found."
        )

    return model


def _get_battery_class() -> dict[str, Any]:
    """Find the Battery YOLO class."""

    model_class = fetch_one(
        """
        SELECT
            mc.model_class_id,
            mc.class_name,
            mc.display_name,
            mc.category_id,
            wc.category_code,
            wc.category_name,
            wc.hazard_level,
            wc.requires_special_handling

        FROM model_classes AS mc

        JOIN waste_categories AS wc
            ON wc.category_id = mc.category_id

        WHERE mc.class_name = 'Battery'
          AND mc.is_active = 1
          AND wc.is_active = 1

        LIMIT 1
        """
    )

    if model_class is None:
        raise RuntimeError(
            "The Battery model class was not found."
        )

    return model_class


def _get_class_threshold(
    model_version_id: int,
    model_class_id: int,
    fallback_threshold: float,
) -> float:
    """Return the Battery class threshold."""

    threshold_row = fetch_one(
        """
        SELECT confidence_threshold

        FROM inference_thresholds

        WHERE model_version_id = %s
          AND model_class_id = %s
        """,
        (
            model_version_id,
            model_class_id,
        ),
    )

    if (
        threshold_row is None
        or threshold_row.get(
            "confidence_threshold"
        ) is None
    ):
        return fallback_threshold

    return float(
        threshold_row["confidence_threshold"]
    )


# ============================================================
# CREATE DEMO YOLO DETECTION
# ============================================================

def _create_demo_detection_session(
    user: dict[str, Any],
    model: dict[str, Any],
    battery_class: dict[str, Any],
) -> tuple[int, int]:
    """
    Create one completed demo detection session.

    This simulates YOLO detecting one battery in an uploaded
    household image.
    """

    model_version_id = int(
        model["model_version_id"]
    )

    model_class_id = int(
        battery_class["model_class_id"]
    )

    global_threshold = float(
        model["global_confidence_threshold"]
    )

    class_threshold = _get_class_threshold(
        model_version_id=model_version_id,
        model_class_id=model_class_id,
        fallback_threshold=global_threshold,
    )

    request_uuid = str(
        uuid4()
    )

    detection_session_id = execute(
        """
        INSERT INTO detection_sessions (
            request_uuid,
            user_id,
            report_id,
            model_version_id,
            source_module,
            original_filename,
            stored_image_path,
            annotated_image_path,
            applied_global_threshold,
            processing_status,
            processing_time_ms,
            error_message,
            completed_at
        )
        VALUES (
            %s,
            %s,
            NULL,
            %s,
            'household',
            'demo_battery.jpg',
            'backend/uploads/demo_battery.jpg',
            'backend/uploads/annotated_demo_battery.jpg',
            %s,
            'completed',
            145,
            NULL,
            NOW()
        )
        """,
        (
            request_uuid,
            user["user_id"],
            model_version_id,
            global_threshold,
        ),
    )

    if not detection_session_id:
        raise RuntimeError(
            "The demo detection session could not be created."
        )

    detected_object_id = execute(
        """
        INSERT INTO detected_objects (
            detection_session_id,
            model_class_id,
            confidence,
            applied_class_threshold,
            bbox_x1,
            bbox_y1,
            bbox_x2,
            bbox_y2
        )
        VALUES (
            %s,
            %s,
            0.93000,
            %s,
            120.00,
            80.00,
            420.00,
            360.00
        )
        """,
        (
            detection_session_id,
            model_class_id,
            class_threshold,
        ),
    )

    if not detected_object_id:
        raise RuntimeError(
            "The demo detected object could not be created."
        )

    return (
        int(detection_session_id),
        int(detected_object_id),
    )


# ============================================================
# COMPLETE HOUSEHOLD RAG TEST
# ============================================================

def main() -> None:
    """
    Test the full offline Household RAG pipeline.

    It checks:

    1. Household user retrieval
    2. YOLO model retrieval
    3. Demo detection-session creation
    4. Detected class-to-category mapping
    5. Verified knowledge retrieval
    6. Household safety-rule retrieval
    7. Facility retrieval
    8. Guidance generation
    9. Response validation
    10. Advice and source-link storage
    """

    print("=" * 60)
    print("STARTING HOUSEHOLD RAG TEST")
    print("=" * 60)

    user = _get_demo_household_user()
    model = _get_current_model()
    battery_class = _get_battery_class()

    print("\n========== TEST HOUSEHOLD ==========")

    pprint(user)

    print("\n========== CURRENT YOLO MODEL ==========")

    pprint(model)

    print("\n========== TEST MODEL CLASS ==========")

    pprint(battery_class)

    (
        detection_session_id,
        detected_object_id,
    ) = _create_demo_detection_session(
        user=user,
        model=model,
        battery_class=battery_class,
    )

    print("\n========== CREATED DETECTION ==========")

    print(
        f"Detection Session ID: {detection_session_id}"
    )

    print(
        f"Detected Object ID: {detected_object_id}"
    )

    result = generate_household_advice_offline(
        user_id=int(user["user_id"]),
        detection_session_id=detection_session_id,
        response_language="en",
    )

    advice_id = int(
        result["advice_id"]
    )

    advice_result = result["result"]

    print("\n========== GENERATED ADVICE ID ==========")

    print(
        f"Advice ID: {advice_id}"
    )

    print("\n========== RESPONSE MODE ==========")

    print(
        advice_result["mode"]
    )

    print("\n========== SUMMARY ==========")

    print(
        advice_result["summary"]
    )

    print("\n========== OVERALL PRIORITY ==========")

    print(
        advice_result["overall_priority"]
    )

    print("\n========== DETECTION RESULT ==========")

    pprint(
        advice_result["detection"]
    )

    print("\n========== HOUSEHOLD GUIDANCE ==========")

    for number, guidance in enumerate(
        advice_result["guidance"],
        start=1,
    ):
        print(
            f"\nGuidance {number}"
        )

        pprint(guidance)

    print("\n========== VERIFIED SOURCES ==========")

    if advice_result["source_list"]:
        for source in advice_result[
            "source_list"
        ]:
            pprint(source)

    else:
        print(
            "No verified household sources were retrieved."
        )

    print("\n========== VERIFIED FACILITIES ==========")

    if advice_result["verified_facilities"]:
        for facility in advice_result[
            "verified_facilities"
        ]:
            pprint(facility)

    else:
        print(
            "No verified facility was found."
        )

    print("\n========== LIMITATIONS ==========")

    for limitation in advice_result[
        "limitations"
    ]:
        print(
            f"- {limitation}"
        )

    # ========================================================
    # VERIFY SAVED ADVICE
    # ========================================================

    saved_advice = fetch_one(
        """
        SELECT
            advice_id,
            detection_session_id,
            audience_role,
            priority_level,
            summary,
            response_language,
            response_json,
            gemini_model,
            prompt_version,
            local_verification_required,
            created_at

        FROM generated_advice

        WHERE advice_id = %s
        """,
        (advice_id,),
    )

    if saved_advice is None:
        raise RuntimeError(
            "The Household RAG advice was not saved."
        )

    print("\n========== SAVED ADVICE RECORD ==========")

    pprint(saved_advice)

    # ========================================================
    # VERIFY SAVED KNOWLEDGE LINKS
    # ========================================================

    knowledge_link_result = fetch_one(
        """
        SELECT COUNT(*) AS total

        FROM advice_knowledge_links

        WHERE advice_id = %s
        """,
        (advice_id,),
    )

    knowledge_link_count = _to_int(
        knowledge_link_result.get("total")
        if knowledge_link_result
        else 0
    )

    print("\n========== KNOWLEDGE AUDIT LINKS ==========")

    print(
        f"Saved knowledge links: {knowledge_link_count}"
    )

    # ========================================================
    # FINAL CHECKS
    # ========================================================

    if advice_result["mode"] != "offline_grounded":
        raise AssertionError(
            "The Household RAG mode should be "
            "offline_grounded."
        )

    if (
        advice_result["overall_priority"]
        != "critical"
    ):
        raise AssertionError(
            "Battery guidance should have critical priority "
            "because of its mandatory safety rule."
        )

    if not advice_result["guidance"]:
        raise AssertionError(
            "No household guidance was generated."
        )

    first_guidance = advice_result[
        "guidance"
    ][0]

    if not first_guidance[
        "safety_rule_ids"
    ]:
        raise AssertionError(
            "The Battery safety rule was not retrieved."
        )

    if saved_advice["audience_role"] != "household":
        raise AssertionError(
            "The saved audience role should be household."
        )

    if saved_advice["priority_level"] != "critical":
        raise AssertionError(
            "The saved advice priority should be critical."
        )

    if not saved_advice["response_json"]:
        raise AssertionError(
            "The Household RAG response JSON was not saved."
        )

    print("\n" + "=" * 60)
    print("HOUSEHOLD RAG TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()