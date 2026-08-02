from datetime import date, datetime
from decimal import Decimal
from typing import Any

from repositories.household_repository import (
    create_household_advice,
    get_detected_objects_for_session,
    get_household_detection_session,
    get_household_safety_rules,
    get_household_user_scope,
    get_verified_household_facilities,
    retrieve_verified_household_knowledge,
    save_household_advice_knowledge_links,
)
from schemas.household_advice_schema import (
    HouseholdAdviceResponse,
    validate_household_advice_response,
)


# ============================================================
# PRIORITY SETTINGS
# ============================================================

PRIORITY_RANK = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


# ============================================================
# GENERAL HELPERS
# ============================================================

def _json_safe_value(
    value: Any,
) -> Any:
    """Convert MySQL values into JSON-safe Python values."""

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, (date, datetime)):
        return value.isoformat()

    if isinstance(value, dict):
        return {
            key: _json_safe_value(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            _json_safe_value(item)
            for item in value
        ]

    return value


def _remove_duplicate_text(
    items: list[str],
) -> list[str]:
    """Remove duplicate and empty instructions."""

    result: list[str] = []
    seen: set[str] = set()

    for item in items:
        if not isinstance(item, str):
            continue

        cleaned_item = item.strip()

        if not cleaned_item:
            continue

        if cleaned_item in seen:
            continue

        seen.add(cleaned_item)
        result.append(cleaned_item)

    return result


def _append_text(
    destination: list[str],
    value: Any,
) -> None:
    """Add a non-empty text value to an instruction list."""

    if value is None:
        return

    if isinstance(value, str):
        cleaned_value = value.strip()

        if cleaned_value:
            destination.append(cleaned_value)


def _maximum_priority(
    priorities: list[str],
) -> str:
    """Return the highest priority from a list."""

    if not priorities:
        return "low"

    valid_priorities = [
        priority
        for priority in priorities
        if priority in PRIORITY_RANK
    ]

    if not valid_priorities:
        return "low"

    return max(
        valid_priorities,
        key=lambda priority: PRIORITY_RANK[priority],
    )


def _hazard_priority(
    hazard_level: str,
    requires_special_handling: bool,
    safety_rules: list[dict[str, Any]],
) -> str:
    """Calculate the handling priority for one waste class."""

    hazard_priority_map = {
        "low": "low",
        "medium": "medium",
        "high": "high",
    }

    priorities = [
        hazard_priority_map.get(
            hazard_level,
            "low",
        )
    ]

    if requires_special_handling:
        priorities.append("high")

    for rule in safety_rules:
        severity = rule.get("severity")

        if severity in PRIORITY_RANK:
            priorities.append(severity)

    return _maximum_priority(priorities)


def _source_page_or_section(
    knowledge: dict[str, Any],
) -> str:
    """Return the recorded page or section for a source."""

    source_section = knowledge.get(
        "source_section"
    )

    if source_section:
        return str(source_section)

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
# FALLBACK GUIDANCE
# ============================================================

def _get_fallback_guidance(
    detected_item: dict[str, Any],
) -> dict[str, list[str]]:
    """
    Return basic conservative instructions when no verified
    Bangladesh knowledge is available.

    These are project safety fallbacks, not official guidance.
    """

    class_name = str(
        detected_item["display_name"]
    )

    category_code = str(
        detected_item["category_code"]
    )

    if category_code == "HAZARDOUS":
        return {
            "immediate_actions": [
                (
                    f"Keep the {class_name} separate from "
                    "ordinary household waste immediately."
                )
            ],
            "segregation_steps": [
                (
                    "Place it in a separate dry, non-metal "
                    "container."
                )
            ],
            "preparation_steps": [
                (
                    "Do not open, crush, puncture, wash or "
                    "dismantle it."
                )
            ],
            "temporary_storage_steps": [
                (
                    "Store it in a cool and dry place away "
                    "from children, heat, water and metal "
                    "objects."
                )
            ],
            "disposal_steps": [
                (
                    "Keep it safely stored until a verified "
                    "hazardous-waste or e-waste collection "
                    "option is confirmed."
                )
            ],
            "safety_precautions": [
                (
                    "Avoid touching leakage and use gloves "
                    "when the item is damaged."
                )
            ],
            "prohibited_actions": [
                (
                    "Do not burn, puncture, crush or place it "
                    "in ordinary mixed waste."
                )
            ],
            "environmental_notes": [
                (
                    "Improper disposal may cause fire and "
                    "contaminate soil, air or water."
                )
            ],
            "recycling_opportunities": [
                (
                    "Specialised handlers may recover useful "
                    "materials from the item."
                )
            ],
        }

    if category_code == "E_WASTE":
        return {
            "immediate_actions": [
                (
                    f"Disconnect and keep the {class_name} "
                    "separate from ordinary household waste."
                )
            ],
            "segregation_steps": [
                (
                    "Place the complete device and its loose "
                    "parts in a separate e-waste area."
                )
            ],
            "preparation_steps": [
                (
                    "Remove personal data when relevant and "
                    "keep the device intact."
                )
            ],
            "temporary_storage_steps": [
                (
                    "Keep the device dry and protected from "
                    "rain, heat and physical damage."
                )
            ],
            "disposal_steps": [
                (
                    "Prefer repair, reuse, donation or a "
                    "verified e-waste collection service."
                )
            ],
            "safety_precautions": [
                (
                    "Use care around broken glass, sharp "
                    "metal, exposed wires and damaged "
                    "batteries."
                )
            ],
            "prohibited_actions": [
                (
                    "Do not burn wires, break circuit boards "
                    "or dismantle the device using unsafe "
                    "methods."
                )
            ],
            "environmental_notes": [
                (
                    "Open dumping may release harmful "
                    "materials and waste recoverable parts."
                )
            ],
            "recycling_opportunities": [
                (
                    "Working devices may be repaired or reused, "
                    "while professional handlers may recover "
                    "metals and components."
                )
            ],
        }

    if category_code == "COMPOSTABLE":
        return {
            "immediate_actions": [
                (
                    f"Separate the {class_name} from plastic, "
                    "glass, batteries and metal."
                )
            ],
            "segregation_steps": [
                (
                    "Place it in a separate organic-waste "
                    "container."
                )
            ],
            "preparation_steps": [
                (
                    "Remove non-organic contamination before "
                    "composting or organic collection."
                )
            ],
            "temporary_storage_steps": [
                (
                    "Use a covered container and avoid storing "
                    "the waste for a long period."
                )
            ],
            "disposal_steps": [
                (
                    "Use a suitable home composting method or "
                    "a confirmed separated organic-waste "
                    "collection option."
                )
            ],
            "safety_precautions": [
                (
                    "Wash hands after handling and clean the "
                    "container regularly."
                )
            ],
            "prohibited_actions": [
                (
                    "Do not mix batteries, glass, metal or "
                    "plastic into compostable waste."
                )
            ],
            "environmental_notes": [
                (
                    "Separated organic waste can reduce mixed "
                    "waste and may be converted into compost."
                )
            ],
            "recycling_opportunities": [
                (
                    "Suitable food and biodegradable waste may "
                    "be recovered through controlled composting."
                )
            ],
        }

    if category_code == "RECYCLABLE_METAL":
        return {
            "immediate_actions": [
                (
                    f"Keep the {class_name} separate from wet "
                    "and hazardous waste."
                )
            ],
            "segregation_steps": [
                (
                    "Place it with separated recyclable metal "
                    "items."
                )
            ],
            "preparation_steps": [
                (
                    "Remove food residue when safe and handle "
                    "sharp edges carefully."
                )
            ],
            "temporary_storage_steps": [
                (
                    "Keep it dry in a stable container."
                )
            ],
            "disposal_steps": [
                (
                    "Transfer it through a confirmed recycling "
                    "or metal-recovery channel."
                )
            ],
            "safety_precautions": [
                (
                    "Use gloves when the object has sharp or "
                    "damaged edges."
                )
            ],
            "prohibited_actions": [
                (
                    "Do not mix contaminated or hazardous metal "
                    "containers with normal recyclables."
                )
            ],
            "environmental_notes": [
                (
                    "Metal recovery can reduce the need for new "
                    "raw materials."
                )
            ],
            "recycling_opportunities": [
                (
                    "Clean separated metal may have material "
                    "recovery value."
                )
            ],
        }

    if category_code == "RECYCLABLE_PAPER":
        return {
            "immediate_actions": [
                (
                    f"Keep the {class_name} clean and separate "
                    "from wet waste."
                )
            ],
            "segregation_steps": [
                (
                    "Place dry paper and cardboard in a separate "
                    "recyclable-paper container."
                )
            ],
            "preparation_steps": [
                (
                    "Remove food, plastic wrapping and other "
                    "non-paper materials when practical."
                )
            ],
            "temporary_storage_steps": [
                (
                    "Keep it dry and flatten large cardboard "
                    "pieces to save space."
                )
            ],
            "disposal_steps": [
                (
                    "Use a confirmed paper-recycling or "
                    "separated collection channel."
                )
            ],
            "safety_precautions": [
                (
                    "Avoid handling paper contaminated with "
                    "unknown chemicals using bare hands."
                )
            ],
            "prohibited_actions": [
                (
                    "Do not mix wet, oily or heavily contaminated "
                    "paper with clean recyclable paper."
                )
            ],
            "environmental_notes": [
                (
                    "Keeping paper dry improves its opportunity "
                    "for material recovery."
                )
            ],
            "recycling_opportunities": [
                (
                    "Clean paper and cardboard may be recycled "
                    "into new paper products."
                )
            ],
        }

    if category_code == "RECYCLABLE_PLASTIC":
        return {
            "immediate_actions": [
                (
                    f"Keep the {class_name} separate from food, "
                    "wet waste and hazardous material."
                )
            ],
            "segregation_steps": [
                (
                    "Place suitable plastic items in a separate "
                    "plastic-recycling container."
                )
            ],
            "preparation_steps": [
                (
                    "Empty the item and remove food residue when "
                    "this can be done safely."
                )
            ],
            "temporary_storage_steps": [
                (
                    "Keep the plastic reasonably clean and dry."
                )
            ],
            "disposal_steps": [
                (
                    "Use a confirmed plastic-recycling or "
                    "separated collection option."
                )
            ],
            "safety_precautions": [
                (
                    "Treat containers that held chemicals, oil "
                    "or pesticides as potentially hazardous."
                )
            ],
            "prohibited_actions": [
                (
                    "Do not openly burn plastic waste."
                )
            ],
            "environmental_notes": [
                (
                    "Open burning releases harmful smoke, while "
                    "littered plastic may block drains and enter "
                    "waterways."
                )
            ],
            "recycling_opportunities": [
                (
                    "Clean and correctly separated plastic may "
                    "be accepted for material recovery."
                )
            ],
        }

    return {
        "immediate_actions": [
            (
                f"Keep the {class_name} separate from mixed "
                "household waste."
            )
        ],
        "segregation_steps": [
            "Place the item in a separate labelled container."
        ],
        "preparation_steps": [
            "Keep the item intact until its handling method is confirmed."
        ],
        "temporary_storage_steps": [
            "Store it in a dry and protected location."
        ],
        "disposal_steps": [
            (
                "Confirm an appropriate local collection or "
                "disposal method before transfer."
            )
        ],
        "safety_precautions": [
            "Use gloves when the item is damaged or contaminated."
        ],
        "prohibited_actions": [
            "Do not burn or dump the item in an open area."
        ],
        "environmental_notes": [
            "Incorrect disposal may harm people and the environment."
        ],
        "recycling_opportunities": [
            "Reuse or recycling may be possible after local confirmation."
        ],
    }


# ============================================================
# KNOWLEDGE-BASED GUIDANCE
# ============================================================

def _build_object_guidance(
    detected_item: dict[str, Any],
    knowledge_rows: list[dict[str, Any]],
    safety_rules: list[dict[str, Any]],
    facilities: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build grounded guidance for one detected waste class."""

    fallback = _get_fallback_guidance(
        detected_item
    )

    immediate_actions: list[str] = []
    segregation_steps: list[str] = []
    preparation_steps: list[str] = []
    temporary_storage_steps: list[str] = []
    disposal_steps: list[str] = []
    safety_precautions: list[str] = []
    prohibited_actions: list[str] = []
    environmental_notes: list[str] = []
    recycling_opportunities: list[str] = []

    source_ids: list[int] = []
    safety_rule_ids: list[int] = []
    facility_ids: list[int] = []

    # Use verified knowledge when it exists.
    for knowledge in knowledge_rows:
        _append_text(
            immediate_actions,
            knowledge.get("immediate_action"),
        )

        _append_text(
            segregation_steps,
            knowledge.get("segregation_advice"),
        )

        _append_text(
            preparation_steps,
            knowledge.get("cleaning_or_preparation"),
        )

        _append_text(
            temporary_storage_steps,
            knowledge.get("temporary_storage"),
        )

        _append_text(
            disposal_steps,
            knowledge.get("disposal_or_transfer_advice"),
        )

        _append_text(
            disposal_steps,
            knowledge.get("alternative_low_tech_solution"),
        )

        _append_text(
            safety_precautions,
            knowledge.get("safety_precautions"),
        )

        _append_text(
            prohibited_actions,
            knowledge.get("prohibited_actions"),
        )

        _append_text(
            environmental_notes,
            knowledge.get("environmental_impact_info"),
        )

        _append_text(
            environmental_notes,
            knowledge.get(
                "consequences_of_improper_disposal"
            ),
        )

        _append_text(
            recycling_opportunities,
            knowledge.get(
                "recycling_or_recovery_opportunities"
            ),
        )

        source_id = knowledge.get("source_id")

        if source_id is not None:
            source_id = int(source_id)

            if source_id not in source_ids:
                source_ids.append(source_id)

    # Add transparent safety rules.
    for safety_rule in safety_rules:
        safety_rule_id = int(
            safety_rule["safety_rule_id"]
        )

        if safety_rule_id not in safety_rule_ids:
            safety_rule_ids.append(
                safety_rule_id
            )

        rule_text = safety_rule.get(
            "rule_text"
        )

        if safety_rule["rule_type"] == "prohibited":
            _append_text(
                prohibited_actions,
                rule_text,
            )

        else:
            _append_text(
                safety_precautions,
                rule_text,
            )

    # Add verified facilities.
    for facility in facilities:
        facility_id = int(
            facility["facility_id"]
        )

        if facility_id not in facility_ids:
            facility_ids.append(
                facility_id
            )

    if facilities:
        disposal_steps.append(
            (
                "A verified facility is listed in the response. "
                "Confirm its opening hours and acceptance rules "
                "before visiting."
            )
        )

    # When no verified knowledge exists, use conservative fallback.
    if not knowledge_rows:
        immediate_actions.extend(
            fallback["immediate_actions"]
        )

        segregation_steps.extend(
            fallback["segregation_steps"]
        )

        preparation_steps.extend(
            fallback["preparation_steps"]
        )

        temporary_storage_steps.extend(
            fallback["temporary_storage_steps"]
        )

        disposal_steps.extend(
            fallback["disposal_steps"]
        )

        safety_precautions.extend(
            fallback["safety_precautions"]
        )

        prohibited_actions.extend(
            fallback["prohibited_actions"]
        )

        environmental_notes.extend(
            fallback["environmental_notes"]
        )

        recycling_opportunities.extend(
            fallback["recycling_opportunities"]
        )

    priority = _hazard_priority(
        hazard_level=str(
            detected_item["hazard_level"]
        ),
        requires_special_handling=bool(
            detected_item[
                "requires_special_handling"
            ]
        ),
        safety_rules=safety_rules,
    )

    return {
        "model_class_id": int(
            detected_item["model_class_id"]
        ),
        "class_name": str(
            detected_item["class_name"]
        ),
        "category_id": int(
            detected_item["category_id"]
        ),
        "category_name": str(
            detected_item["category_name"]
        ),
        "priority": priority,
        "immediate_actions": _remove_duplicate_text(
            immediate_actions
        ),
        "segregation_steps": _remove_duplicate_text(
            segregation_steps
        ),
        "preparation_steps": _remove_duplicate_text(
            preparation_steps
        ),
        "temporary_storage_steps": _remove_duplicate_text(
            temporary_storage_steps
        ),
        "disposal_steps": _remove_duplicate_text(
            disposal_steps
        ),
        "safety_precautions": _remove_duplicate_text(
            safety_precautions
        ),
        "prohibited_actions": _remove_duplicate_text(
            prohibited_actions
        ),
        "environmental_notes": _remove_duplicate_text(
            environmental_notes
        ),
        "recycling_opportunities": _remove_duplicate_text(
            recycling_opportunities
        ),
        "safety_rule_ids": safety_rule_ids,
        "source_ids": source_ids,
        "facility_ids": facility_ids,
        "verified_knowledge_found": bool(
            knowledge_rows
        ),
        "human_review_required": (
            priority in {"high", "critical"}
            or not knowledge_rows
        ),
    }


# ============================================================
# DETECTION OUTPUT
# ============================================================

def _build_detected_objects(
    detected_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Convert detected-object database rows into response data."""

    detected_objects: list[dict[str, Any]] = []

    for row in detected_rows:
        confidence_value = row.get(
            "confidence"
        )

        confidence = (
            float(confidence_value)
            if confidence_value is not None
            else None
        )

        detected_objects.append(
            {
                "detected_object_id": int(
                    row["detected_object_id"]
                ),
                "model_class_id": int(
                    row["model_class_id"]
                ),
                "class_name": str(
                    row["class_name"]
                ),
                "display_name": str(
                    row["display_name"]
                ),
                "category_id": int(
                    row["category_id"]
                ),
                "category_code": str(
                    row["category_code"]
                ),
                "category_name": str(
                    row["category_name"]
                ),
                "confidence": confidence,
                "hazard_level": str(
                    row["hazard_level"]
                ),
                "requires_special_handling": bool(
                    row[
                        "requires_special_handling"
                    ]
                ),
            }
        )

    return detected_objects


def _get_unique_detected_classes(
    detected_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Return one row for each detected model class.

    One image may contain several objects of the same class,
    but guidance only needs to be produced once per class.
    """

    unique_classes: list[dict[str, Any]] = []
    seen_model_class_ids: set[int] = set()

    for row in detected_rows:
        model_class_id = int(
            row["model_class_id"]
        )

        if model_class_id in seen_model_class_ids:
            continue

        seen_model_class_ids.add(
            model_class_id
        )

        unique_classes.append(
            row
        )

    return unique_classes


# ============================================================
# SOURCE AND FACILITY LISTS
# ============================================================

def _build_source_list(
    knowledge_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build a unique list of verified official sources."""

    sources_by_id: dict[int, dict[str, Any]] = {}

    for knowledge in knowledge_rows:
        source_id_value = knowledge.get(
            "source_id"
        )

        if source_id_value is None:
            continue

        source_id = int(
            source_id_value
        )

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

        last_checked_at = (
            knowledge.get("last_checked_at")
            or knowledge.get(
                "last_source_check_at"
            )
        )

        sources_by_id[source_id] = {
            "source_id": source_id,
            "title": str(
                knowledge.get("source_title")
                or "Untitled official source"
            ),
            "issuing_authority": str(
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
                str(_json_safe_value(last_checked_at))
                if last_checked_at is not None
                else None
            ),
            "source_url": knowledge.get(
                "source_url"
            ),
        }

    return list(
        sources_by_id.values()
    )


def _deduplicate_facilities(
    facilities: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Remove repeated facilities retrieved for several classes."""

    facilities_by_id: dict[int, dict[str, Any]] = {}

    for facility in facilities:
        facility_id = int(
            facility["facility_id"]
        )

        if facility_id not in facilities_by_id:
            facilities_by_id[facility_id] = (
                _json_safe_value(
                    facility
                )
            )

    return list(
        facilities_by_id.values()
    )


def _deduplicate_knowledge(
    knowledge_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Remove repeated knowledge before saving audit links."""

    knowledge_by_id: dict[int, dict[str, Any]] = {}

    for row in knowledge_rows:
        knowledge_id = int(
            row["knowledge_id"]
        )

        if knowledge_id not in knowledge_by_id:
            knowledge_by_id[knowledge_id] = row

    return list(
        knowledge_by_id.values()
    )


# ============================================================
# COMPLETE HOUSEHOLD RAG PIPELINE
# ============================================================

def generate_household_advice_offline(
    user_id: int,
    detection_session_id: int,
    response_language: str = "en",
) -> dict[str, Any]:
    """
    Run the complete Household RAG pipeline without Gemini.

    Pipeline:

    1. Validate household user.
    2. Read completed YOLO detection.
    3. Map detected classes to waste categories.
    4. Retrieve verified Bangladesh knowledge.
    5. Retrieve safety rules.
    6. Retrieve verified local facilities.
    7. Create grounded household guidance.
    8. Validate the response.
    9. Save advice and knowledge audit links.
    """

    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError(
            "user_id must be a positive integer."
        )

    if (
        not isinstance(detection_session_id, int)
        or detection_session_id <= 0
    ):
        raise ValueError(
            "detection_session_id must be a "
            "positive integer."
        )

    if response_language != "en":
        raise ValueError(
            "Offline Household RAG currently supports "
            "English only. Bangla will be enabled during "
            "Gemini integration."
        )

    household = get_household_user_scope(
        user_id
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

    detected_rows = (
        get_detected_objects_for_session(
            detection_session_id
        )
    )

    if not detected_rows:
        raise ValueError(
            "The detection session contains no "
            "recognised waste objects."
        )

    region_id_value = household.get(
        "region_id"
    )

    region_id = (
        int(region_id_value)
        if region_id_value is not None
        else None
    )

    unique_detected_classes = (
        _get_unique_detected_classes(
            detected_rows
        )
    )

    guidance: list[dict[str, Any]] = []
    all_knowledge_rows: list[dict[str, Any]] = []
    all_facilities: list[dict[str, Any]] = []
    limitations: list[str] = [
        (
            "Gemini was not used. This response was "
            "created from detected classes, project safety "
            "rules and verified database retrieval."
        )
    ]

    object_priorities: list[str] = []

    for detected_item in unique_detected_classes:
        model_class_id = int(
            detected_item["model_class_id"]
        )

        category_id = int(
            detected_item["category_id"]
        )

        knowledge_rows = (
            retrieve_verified_household_knowledge(
                model_class_id=model_class_id,
                category_id=category_id,
                region_id=region_id,
                limit=5,
            )
        )

        safety_rules = (
            get_household_safety_rules(
                model_class_id=model_class_id,
                category_id=category_id,
            )
        )

        facilities = (
            get_verified_household_facilities(
                region_id=region_id,
                category_id=category_id,
            )
        )

        item_guidance = _build_object_guidance(
            detected_item=detected_item,
            knowledge_rows=knowledge_rows,
            safety_rules=safety_rules,
            facilities=facilities,
        )

        guidance.append(
            item_guidance
        )

        object_priorities.append(
            item_guidance["priority"]
        )

        all_knowledge_rows.extend(
            knowledge_rows
        )

        all_facilities.extend(
            facilities
        )

        if not knowledge_rows:
            limitations.append(
                (
                    "No verified Bangladesh household "
                    "knowledge was available for "
                    f"{detected_item['display_name']}. "
                    "Conservative project fallback guidance "
                    "was used."
                )
            )

        if (
            not facilities
            and bool(
                detected_item[
                    "requires_special_handling"
                ]
            )
        ):
            limitations.append(
                (
                    "No verified local facility was found "
                    f"for {detected_item['display_name']}."
                )
            )

    if region_id is None:
        limitations.append(
            (
                "The household user has no assigned region, "
                "so local facility retrieval was skipped."
            )
        )

    limitations = _remove_duplicate_text(
        limitations
    )

    unique_knowledge_rows = (
        _deduplicate_knowledge(
            all_knowledge_rows
        )
    )

    verified_facilities = (
        _deduplicate_facilities(
            all_facilities
        )
    )

    overall_priority = _maximum_priority(
        object_priorities
    )

    detected_object_count = len(
        detected_rows
    )

    detected_class_count = len(
        unique_detected_classes
    )

    summary = (
        f"Detected {detected_object_count} waste object(s) "
        f"across {detected_class_count} waste class(es). "
        f"The overall handling priority is "
        f"{overall_priority}."
    )

    response: HouseholdAdviceResponse = {
        "mode": "offline_grounded",
        "response_language": response_language,
        "household": {
            "user_id": int(
                household["user_id"]
            ),
            "full_name": str(
                household["full_name"]
            ),
            "region_id": region_id,
            "region_name": (
                str(household["region_name"])
                if household.get("region_name")
                is not None
                else None
            ),
            "region_type": (
                str(household["region_type"])
                if household.get("region_type")
                is not None
                else None
            ),
        },
        "detection": {
            "detection_session_id": int(
                detection_session[
                    "detection_session_id"
                ]
            ),
            "request_uuid": str(
                detection_session[
                    "request_uuid"
                ]
            ),
            "original_filename": str(
                detection_session[
                    "original_filename"
                ]
            ),
            "model_version": str(
                detection_session[
                    "version_name"
                ]
            ),
            "architecture": str(
                detection_session[
                    "architecture"
                ]
            ),
            "detected_objects": (
                _build_detected_objects(
                    detected_rows
                )
            ),
        },
        "overall_priority": overall_priority,
        "summary": summary,
        "guidance": guidance,
        "source_list": (
            _build_source_list(
                unique_knowledge_rows
            )
        ),
        "verified_facilities": (
            verified_facilities
        ),
        "limitations": limitations,
        "local_verification_required": True,
        "disclaimer": (
            "This result is household decision-support "
            "information. Confirm local collection rules "
            "and facility acceptance before transferring "
            "waste. Do not use the result as emergency, "
            "medical or legal advice."
        ),
    }

    validated_response = (
        validate_household_advice_response(
            response
        )
    )

    advice_id = create_household_advice(
        detection_session_id=(
            detection_session_id
        ),
        priority_level=overall_priority,
        summary=summary,
        response_language=response_language,
        response_payload=validated_response,
        prompt_version=(
            "offline-household-rag-1.0"
        ),
    )

    save_household_advice_knowledge_links(
        advice_id=advice_id,
        knowledge_rows=(
            unique_knowledge_rows
        ),
    )

    return {
        "advice_id": advice_id,
        "detection_session_id": (
            detection_session_id
        ),
        "result": validated_response,
    }