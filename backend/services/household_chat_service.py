import json
from typing import Any

from repositories.household_repository import (
    get_detected_objects_for_session,
    get_household_advice_by_id,
    get_household_detection_session,
    get_household_safety_rules,
    get_household_user_scope,
    get_verified_household_facilities,
    retrieve_verified_household_knowledge,
)


def _parse_saved_json(
    value: Any,
) -> Any:
    """
    Convert stored MySQL JSON text into Python data.
    """

    if value is None:
        return None

    if isinstance(
        value,
        (
            dict,
            list,
        ),
    ):
        return value

    if isinstance(
        value,
        bytes,
    ):
        value = value.decode(
            "utf-8"
        )

    if not isinstance(
        value,
        str,
    ):
        return value

    try:
        return json.loads(
            value
        )

    except json.JSONDecodeError:
        return value


def _unique_detected_classes(
    detected_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Keep one row for every detected model class.

    get_detected_objects_for_session() returns the rows used by
    the existing Household RAG pipeline. Follow-up chat only needs
    one grounding bundle for each distinct model class.
    """

    unique_rows: list[
        dict[str, Any]
    ] = []

    seen_model_class_ids: set[
        int
    ] = set()

    for row in detected_rows:
        model_class_id = int(
            row["model_class_id"]
        )

        if (
            model_class_id
            in seen_model_class_ids
        ):
            continue

        seen_model_class_ids.add(
            model_class_id
        )

        unique_rows.append(
            row
        )

    return unique_rows


def build_household_chat_context(
    *,
    user_id: int,
    detection_session_id: int,
    advice_id: int,
) -> dict[str, Any]:
    """
    Build verified grounding for a Household follow-up question.

    This intentionally does NOT:
    - run YOLO again;
    - generate another initial Household advice record;
    - change any detected class.

    The context is rebuilt from the completed detection and the
    same verified Household RAG sources used by the existing
    initial-advice pipeline.
    """

    if (
        not isinstance(
            user_id,
            int,
        )
        or user_id <= 0
    ):
        raise ValueError(
            "user_id must be a positive integer."
        )

    if (
        not isinstance(
            detection_session_id,
            int,
        )
        or detection_session_id <= 0
    ):
        raise ValueError(
            "detection_session_id must be a positive integer."
        )

    if (
        not isinstance(
            advice_id,
            int,
        )
        or advice_id <= 0
    ):
        raise ValueError(
            "advice_id must be a positive integer."
        )

    household = (
        get_household_user_scope(
            user_id
        )
    )

    if household is None:
        raise ValueError(
            "Active household user was not found."
        )

    detection_session = (
        get_household_detection_session(
            detection_session_id=(
                detection_session_id
            ),
            user_id=user_id,
        )
    )

    if detection_session is None:
        raise ValueError(
            "Completed household detection session "
            "was not found for this user."
        )

    advice = (
        get_household_advice_by_id(
            advice_id=advice_id,
            user_id=user_id,
        )
    )

    if advice is None:
        raise ValueError(
            "Household advice was not found, "
            "or it does not belong to this user."
        )

    if (
        int(
            advice[
                "detection_session_id"
            ]
        )
        != detection_session_id
    ):
        raise ValueError(
            "The selected advice does not belong "
            "to this detection session."
        )

    detected_rows = (
        get_detected_objects_for_session(
            detection_session_id
        )
    )

    if not detected_rows:
        raise ValueError(
            "No waste class could be detected from this image. "
            "Please upload a clearer image where the waste objects "
            "are clearly visible and try again."
        )

    region_id_value = (
        household.get(
            "region_id"
        )
    )

    region_id = (
        int(
            region_id_value
        )
        if region_id_value
        is not None
        else None
    )

    unique_classes = (
        _unique_detected_classes(
            detected_rows
        )
    )

    class_grounding: list[
        dict[str, Any]
    ] = []

    for detected_item in (
        unique_classes
    ):
        model_class_id = int(
            detected_item[
                "model_class_id"
            ]
        )

        category_id = int(
            detected_item[
                "category_id"
            ]
        )

        knowledge = (
            retrieve_verified_household_knowledge(
                model_class_id=(
                    model_class_id
                ),
                category_id=(
                    category_id
                ),
                region_id=(
                    region_id
                ),
                limit=5,
            )
        )

        safety_rules = (
            get_household_safety_rules(
                model_class_id=(
                    model_class_id
                ),
                category_id=(
                    category_id
                ),
            )
        )

        facilities = (
            get_verified_household_facilities(
                region_id=(
                    region_id
                ),
                category_id=(
                    category_id
                ),
            )
        )

        class_grounding.append(
            {
                "detected_waste": {
                    "model_class_id":
                        model_class_id,

                    "class_name":
                        detected_item.get(
                            "class_name"
                        ),

                    "display_name":
                        detected_item.get(
                            "display_name"
                        ),

                    "category_id":
                        category_id,

                    "category_code":
                        detected_item.get(
                            "category_code"
                        ),

                    "category_name":
                        detected_item.get(
                            "category_name"
                        ),

                    "hazard_level":
                        detected_item.get(
                            "hazard_level"
                        ),

                    "requires_special_handling":
                        bool(
                            detected_item.get(
                                "requires_special_handling"
                            )
                        ),

                    "confidence":
                        (
                            float(
                                detected_item[
                                    "confidence"
                                ]
                            )
                            if detected_item.get(
                                "confidence"
                            )
                            is not None
                            else None
                        ),
                },

                "verified_knowledge":
                    knowledge,

                "safety_rules":
                    safety_rules,

                "verified_facilities":
                    facilities,
            }
        )

    initial_advice = (
        _parse_saved_json(
            advice.get(
                "response_json"
            )
        )
    )

    return {
        "household": {
            "user_id":
                int(
                    household[
                        "user_id"
                    ]
                ),

            "full_name":
                household.get(
                    "full_name"
                ),

            "region_id":
                region_id,

            "region_name":
                household.get(
                    "region_name"
                ),

            "region_type":
                household.get(
                    "region_type"
                ),
        },

        "detection": {
            "detection_session_id":
                int(
                    detection_session[
                        "detection_session_id"
                    ]
                ),

            "request_uuid":
                detection_session.get(
                    "request_uuid"
                ),

            "original_filename":
                detection_session.get(
                    "original_filename"
                ),

            "model_version":
                detection_session.get(
                    "version_name"
                ),

            "architecture":
                detection_session.get(
                    "architecture"
                ),

            "detected_objects":
                detected_rows,
        },

        "initial_advice": {
            "advice_id":
                int(
                    advice[
                        "advice_id"
                    ]
                ),

            "priority_level":
                advice.get(
                    "priority_level"
                ),

            "summary":
                advice.get(
                    "summary"
                ),

            "response_language":
                advice.get(
                    "response_language"
                ),

            "gemini_model":
                advice.get(
                    "gemini_model"
                ),

            "prompt_version":
                advice.get(
                    "prompt_version"
                ),

            "result":
                initial_advice,
        },

        "class_grounding":
            class_grounding,
    }