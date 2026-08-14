from datetime import date, datetime
from decimal import Decimal
from typing import Any

from repositories.employee_repository import (
    create_employee_advice,
    get_assignment_detection_session,
    get_detected_objects_for_employee_assignment,
    get_employee_assignment,
    get_employee_safety_rules,
    get_employee_scope,
    get_verified_employee_facilities,
    retrieve_verified_employee_knowledge,
    save_employee_advice_knowledge_links,
)
from schemas.employee_advice_schema import (
    EmployeeAdviceResponse,
    validate_employee_advice_response,
)


PROMPT_VERSION = "offline-employee-rag-1.0"

PRIORITY_ORDER = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}

# The assignment table uses "urgent".
# The Employee RAG response uses "critical".
ASSIGNMENT_PRIORITY_MAP = {
    "low": "low",
    "medium": "medium",
    "high": "high",
    "urgent": "critical",
    "critical": "critical",
}


# ============================================================
# GENERAL HELPERS
# ============================================================

def _text(
    value: Any,
    default: str = "",
) -> str:
    """Convert a database value into clean text."""

    if value is None:
        return default

    cleaned = str(value).strip()

    if not cleaned:
        return default

    return cleaned


def _number(
    value: Any,
    default: float | None = None,
) -> float | None:
    """Convert MySQL numeric values into Python floats."""

    if value is None:
        return default

    if isinstance(value, Decimal):
        return float(value)

    return float(value)


def _iso(
    value: Any,
) -> str | None:
    """Convert MySQL date values into ISO text."""

    if value is None:
        return None

    if isinstance(value, (date, datetime)):
        return value.isoformat()

    return str(value)


def _unique_strings(
    values: list[str],
) -> list[str]:
    """Remove empty and repeated text values."""

    result: list[str] = []
    seen: set[str] = set()

    for value in values:
        cleaned = _text(value)

        if not cleaned:
            continue

        comparison_value = cleaned.casefold()

        if comparison_value in seen:
            continue

        seen.add(comparison_value)
        result.append(cleaned)

    return result


def _unique_integers(
    values: list[int],
) -> list[int]:
    """Remove repeated integer IDs."""

    result: list[int] = []
    seen: set[int] = set()

    for value in values:
        number = int(value)

        if number in seen:
            continue

        seen.add(number)
        result.append(number)

    return result


def _higher_priority(
    first: str,
    second: str,
) -> str:
    """Return the higher of two priorities."""

    first_value = PRIORITY_ORDER.get(
        first,
        2,
    )

    second_value = PRIORITY_ORDER.get(
        second,
        2,
    )

    if second_value > first_value:
        return second

    return first


def _get_object_priority(
    detected_object: dict[str, Any],
    assignment_priority: str,
) -> str:
    """
    Calculate the work priority using waste hazard and
    assignment priority.
    """

    hazard_level = _text(
        detected_object.get(
            "hazard_level"
        ),
        "medium",
    ).lower()

    special_handling = bool(
        detected_object.get(
            "requires_special_handling"
        )
    )

    if (
        hazard_level == "high"
        or special_handling
    ):
        object_priority = "critical"

    elif hazard_level == "medium":
        object_priority = "high"

    else:
        object_priority = "medium"

    return _higher_priority(
        object_priority,
        assignment_priority,
    )


def _knowledge_texts(
    row: dict[str, Any],
) -> list[str]:
    """
    Read instruction text from a verified knowledge record.

    Different knowledge views may use different column names,
    so this helper checks the possible text columns.
    """

    possible_fields = (
        "guidance_text",
        "instruction_text",
        "content_text",
        "knowledge_text",
        "content",
        "summary",
        "description",
        "advice_text",
    )

    texts: list[str] = []

    for field_name in possible_fields:
        value = row.get(field_name)

        if not isinstance(value, str):
            continue

        cleaned = value.strip()

        if cleaned:
            texts.append(cleaned)

    return _unique_strings(texts)


def _deduplicate_knowledge_rows(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Remove repeated knowledge records."""

    result: list[dict[str, Any]] = []
    seen: set[int] = set()

    for row in rows:
        knowledge_id = row.get(
            "knowledge_id"
        )

        if knowledge_id is None:
            continue

        knowledge_id = int(
            knowledge_id
        )

        if knowledge_id in seen:
            continue

        seen.add(knowledge_id)
        result.append(row)

    return result


# ============================================================
# DEFAULT WORK INSTRUCTIONS
# ============================================================

def _base_work_instructions(
    class_name: str,
    category_name: str,
    priority: str,
    special_handling: bool,
) -> dict[str, list[str]]:
    """
    Create conservative worker instructions.

    Verified knowledge and safety rules are added later.
    """

    instructions = {
        "ppe_requirements": [
            (
                "Wear durable gloves, closed safety boots "
                "and a reflective vest before starting."
            ),
        ],

        "site_preparation_steps": [
            (
                "Inspect the work area and keep members of "
                "the public away from the collection zone."
            ),
            (
                "Check for sharp objects, leakage, smoke "
                "and unstable waste piles."
            ),
        ],

        "collection_steps": [
            (
                f"Collect {class_name} using suitable tools "
                "instead of direct bare-hand contact."
            ),
        ],

        "segregation_steps": [
            (
                f"Keep {class_name} separate from waste that "
                f"does not belong to {category_name}."
            ),
        ],

        "handling_precautions": [
            (
                "Handle the waste carefully and avoid actions "
                "that may release dust, liquid or sharp parts."
            ),
        ],

        "temporary_storage_steps": [
            (
                "Place the waste in a stable and labelled "
                "container or collection bag."
            ),
        ],

        "transport_steps": [
            (
                "Secure the container before transport so "
                "the waste cannot spill, fall or mix."
            ),
        ],

        "prohibited_actions": [
            (
                "Do not burn, dump or mix the waste with an "
                "incompatible waste stream."
            ),
            (
                "Do not collect unknown or visibly dangerous "
                "material with bare hands."
            ),
        ],

        "emergency_actions": [
            (
                "Stop work and inform the supervising authority "
                "if there is fire, leakage, injury or an unknown "
                "hazardous substance."
            ),
        ],

        "reporting_steps": [
            (
                "Record the waste type, approximate amount, "
                "location and any safety issue found."
            ),
            (
                "Upload completion evidence and update the "
                "assignment status after the site is cleared."
            ),
        ],
    }

    if priority in {
        "high",
        "critical",
    }:
        instructions[
            "ppe_requirements"
        ].append(
            (
                "Use a mask and eye protection when dust, "
                "splashing or harmful contact is possible."
            )
        )

    if special_handling:
        instructions[
            "segregation_steps"
        ].append(
            (
                "Keep this special-handling waste in its own "
                "container and do not compact it."
            )
        )

        instructions[
            "temporary_storage_steps"
        ].append(
            (
                "Keep the container closed and away from heat, "
                "water and public access."
            )
        )

    return instructions


# ============================================================
# APPLY SAFETY RULES
# ============================================================

def _apply_safety_rules(
    safety_rules: list[dict[str, Any]],
    instructions: dict[str, list[str]],
) -> list[int]:
    """
    Add retrieved safety rules to the worker instructions.
    """

    safety_rule_ids: list[int] = []

    for rule in safety_rules:
        rule_id = rule.get(
            "safety_rule_id"
        )

        rule_text = _text(
            rule.get("rule_text")
        )

        rule_type = _text(
            rule.get("rule_type")
        ).lower()

        if rule_id is not None:
            safety_rule_ids.append(
                int(rule_id)
            )

        if not rule_text:
            continue

        if rule_type == "prohibited":
            instructions[
                "prohibited_actions"
            ].append(rule_text)

        elif rule_type == "warning":
            instructions[
                "handling_precautions"
            ].append(rule_text)

        else:
            lowered_text = (
                rule_text.casefold()
            )

            ppe_words = (
                "glove",
                "mask",
                "boot",
                "goggle",
                "eye protection",
                "ppe",
            )

            if any(
                word in lowered_text
                for word in ppe_words
            ):
                instructions[
                    "ppe_requirements"
                ].append(rule_text)

            else:
                instructions[
                    "handling_precautions"
                ].append(rule_text)

    return _unique_integers(
        safety_rule_ids
    )


# ============================================================
# APPLY VERIFIED KNOWLEDGE
# ============================================================

def _apply_verified_knowledge(
    knowledge_rows: list[dict[str, Any]],
    instructions: dict[str, list[str]],
) -> None:
    """
    Add retrieved verified knowledge to the worker guidance.
    """

    for knowledge_row in knowledge_rows:
        retrieved_texts = _knowledge_texts(
            knowledge_row
        )

        instructions[
            "handling_precautions"
        ].extend(retrieved_texts)


def _finalize_instruction_lists(
    instructions: dict[str, list[str]],
) -> None:
    """Remove repeated instructions."""

    for field_name, values in (
        instructions.items()
    ):
        instructions[field_name] = (
            _unique_strings(values)
        )


# ============================================================
# SOURCE FORMATTING
# ============================================================

def _format_source(
    row: dict[str, Any],
) -> dict[str, Any]:
    """Format a verified knowledge source for the response."""

    source: dict[str, Any] = {
        "knowledge_id": int(
            row["knowledge_id"]
        ),

        "retrieval_method": _text(
            row.get("retrieval_method"),
            "manual",
        ),

        "retrieval_score": float(
            row.get(
                "retrieval_score"
            )
            or 0
        ),
    }

    possible_fields = {
        "source_id": (
            "source_id",
        ),

        "source_title": (
            "source_title",
            "title",
        ),

        "source_organization": (
            "source_organization",
            "organization_name",
            "publisher",
        ),

        "source_url": (
            "source_url",
            "url",
        ),

        "topic": (
            "topic",
            "topic_code",
            "knowledge_topic",
        ),
    }

    for (
        output_field,
        source_fields,
    ) in possible_fields.items():

        for source_field in source_fields:
            value = row.get(
                source_field
            )

            if value is None:
                continue

            if output_field == "source_id":
                source[output_field] = int(
                    value
                )

            else:
                cleaned = _text(value)

                if cleaned:
                    source[output_field] = (
                        cleaned
                    )

            break

    return source


# ============================================================
# FACILITY FORMATTING
# ============================================================

def _format_facility(
    row: dict[str, Any],
) -> dict[str, Any]:
    """Format a verified transfer facility."""

    facility: dict[str, Any] = {
        "facility_id": int(
            row["facility_id"]
        ),

        "facility_name": _text(
            row.get("facility_name"),
            "Unnamed facility",
        ),

        "facility_type": _text(
            row.get("facility_type"),
            "unspecified",
        ),

        "region_id": int(
            row["region_id"]
        ),

        "region_name": _text(
            row.get("region_name"),
            "Unknown region",
        ),

        "address_text": _text(
            row.get("address_text"),
            "Address not provided",
        ),
    }

    optional_fields = (
        "phone",
        "email",
        "opening_hours",
        "acceptance_notes",
    )

    for field_name in optional_fields:
        value = _text(
            row.get(field_name)
        )

        if value:
            facility[field_name] = value

    latitude = _number(
        row.get("latitude")
    )

    longitude = _number(
        row.get("longitude")
    )

    if latitude is not None:
        facility["latitude"] = latitude

    if longitude is not None:
        facility["longitude"] = longitude

    return facility


def _deduplicate_facilities(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Remove repeated facilities."""

    result: list[dict[str, Any]] = []
    seen: set[int] = set()

    for row in rows:
        facility_id = row.get(
            "facility_id"
        )

        if facility_id is None:
            continue

        facility_id = int(
            facility_id
        )

        if facility_id in seen:
            continue

        seen.add(facility_id)

        result.append(
            _format_facility(row)
        )

    return result


# ============================================================
# MAIN EMPLOYEE RAG SERVICE
# ============================================================

def generate_employee_advice_offline(
    employee_id: int,
    assignment_id: int,
    response_language: str = "en",
) -> dict[str, Any]:
    """
    Generate Employee RAG instructions without Gemini.

    The response uses:

    - employee information
    - assigned cleanup task
    - completed YOLO detection
    - worker safety rules
    - verified employee knowledge
    - verified disposal facilities
    """

    # --------------------------------------------------------
    # VALIDATE INPUT
    # --------------------------------------------------------

    if employee_id <= 0:
        raise ValueError(
            "employee_id must be greater than zero."
        )

    if assignment_id <= 0:
        raise ValueError(
            "assignment_id must be greater than zero."
        )

    response_language = (
        response_language.strip().lower()
    )

    if response_language not in {
        "en",
        "bn",
    }:
        raise ValueError(
            "response_language must be 'en' or 'bn'."
        )

    if response_language == "bn":
        raise ValueError(
            "Bangla Employee guidance will be enabled "
            "during Gemini integration. Use 'en' for now."
        )

    # --------------------------------------------------------
    # GET EMPLOYEE
    # --------------------------------------------------------

    employee = get_employee_scope(
        employee_id
    )

    if employee is None:
        raise ValueError(
            "An active approved employee account "
            "was not found."
        )

    # --------------------------------------------------------
    # GET ASSIGNMENT
    # --------------------------------------------------------

    assignment = get_employee_assignment(
        assignment_id=assignment_id,
        employee_id=employee_id,
    )

    if assignment is None:
        raise ValueError(
            "The assignment was not found or does not "
            "belong to this employee."
        )

    # --------------------------------------------------------
    # GET YOLO DETECTION
    # --------------------------------------------------------

    detection = (
        get_assignment_detection_session(
            assignment_id=assignment_id,
            employee_id=employee_id,
        )
    )

    if detection is None:
        raise ValueError(
            "No completed YOLO detection is connected "
            "to this assignment."
        )

    detection_session_id = int(
        detection[
            "detection_session_id"
        ]
    )

    detected_objects = (
        get_detected_objects_for_employee_assignment(
            detection_session_id
        )
    )

    if not detected_objects:
        raise ValueError(
            "The completed detection contains no "
            "active detected objects."
        )

    # --------------------------------------------------------
    # ASSIGNMENT PRIORITY
    # --------------------------------------------------------

    database_priority = _text(
        assignment.get(
            "assignment_priority"
        ),
        "medium",
    ).lower()

    assignment_priority = (
        ASSIGNMENT_PRIORITY_MAP.get(
            database_priority,
            "medium",
        )
    )

    # --------------------------------------------------------
    # REGION
    # --------------------------------------------------------

    region_value = assignment.get(
        "region_id",
        employee.get("region_id"),
    )

    region_id = (
        int(region_value)
        if region_value is not None
        else None
    )

    # --------------------------------------------------------
    # GROUP DUPLICATE DETECTED CLASSES
    # --------------------------------------------------------

    grouped_objects: dict[
        tuple[int, int],
        dict[str, Any],
    ] = {}

    for detected_object in detected_objects:
        key = (
            int(
                detected_object[
                    "model_class_id"
                ]
            ),

            int(
                detected_object[
                    "category_id"
                ]
            ),
        )

        previous = grouped_objects.get(
            key
        )

        if previous is None:
            grouped_objects[key] = dict(
                detected_object
            )
            continue

        current_confidence = (
            _number(
                detected_object.get(
                    "confidence"
                ),
                0.0,
            )
            or 0.0
        )

        previous_confidence = (
            _number(
                previous.get(
                    "confidence"
                ),
                0.0,
            )
            or 0.0
        )

        if (
            current_confidence
            > previous_confidence
        ):
            grouped_objects[key] = dict(
                detected_object
            )

    # --------------------------------------------------------
    # BUILD GUIDANCE
    # --------------------------------------------------------

    work_instructions: list[
        dict[str, Any]
    ] = []

    all_knowledge_rows: list[
        dict[str, Any]
    ] = []

    all_facility_rows: list[
        dict[str, Any]
    ] = []

    limitations: list[str] = []

    overall_priority = (
        assignment_priority
    )

    local_verification_required = False

    for detected_object in (
        grouped_objects.values()
    ):
        model_class_id = int(
            detected_object[
                "model_class_id"
            ]
        )

        category_id = int(
            detected_object[
                "category_id"
            ]
        )

        class_name = _text(
            detected_object.get(
                "display_name"
            )
            or detected_object.get(
                "class_name"
            ),
            "Detected waste",
        )

        category_name = _text(
            detected_object.get(
                "category_name"
            ),
            "Unspecified waste category",
        )

        special_handling = bool(
            detected_object.get(
                "requires_special_handling"
            )
        )

        priority = _get_object_priority(
            detected_object,
            assignment_priority,
        )

        overall_priority = (
            _higher_priority(
                overall_priority,
                priority,
            )
        )

        # ----------------------------------------------------
        # RETRIEVE RAG INFORMATION
        # ----------------------------------------------------

        safety_rules = (
            get_employee_safety_rules(
                model_class_id=(
                    model_class_id
                ),
                category_id=category_id,
            )
        )

        knowledge_rows = (
            retrieve_verified_employee_knowledge(
                model_class_id=(
                    model_class_id
                ),
                category_id=category_id,
                region_id=region_id,
                limit=6,
            )
        )

        facility_rows = (
            get_verified_employee_facilities(
                region_id=region_id,
                category_id=category_id,
            )
        )

        all_knowledge_rows.extend(
            knowledge_rows
        )

        all_facility_rows.extend(
            facility_rows
        )

        # ----------------------------------------------------
        # CREATE WORK INSTRUCTIONS
        # ----------------------------------------------------

        instructions = (
            _base_work_instructions(
                class_name=class_name,
                category_name=(
                    category_name
                ),
                priority=priority,
                special_handling=(
                    special_handling
                ),
            )
        )

        safety_rule_ids = (
            _apply_safety_rules(
                safety_rules,
                instructions,
            )
        )

        _apply_verified_knowledge(
            knowledge_rows,
            instructions,
        )

        # ----------------------------------------------------
        # FACILITY TRANSFER GUIDANCE
        # ----------------------------------------------------

        if facility_rows:
            facility_name = _text(
                facility_rows[0].get(
                    "facility_name"
                ),
                "the verified facility",
            )

            instructions[
                "transport_steps"
            ].append(
                (
                    "Confirm acceptance before "
                    "transferring the waste to "
                    f"{facility_name}."
                )
            )

        else:
            instructions[
                "transport_steps"
            ].append(
                (
                    "Ask the supervising authority to "
                    "confirm an approved transfer point "
                    "before leaving the site."
                )
            )

        _finalize_instruction_lists(
            instructions
        )

        # ----------------------------------------------------
        # SOURCE AND FACILITY IDS
        # ----------------------------------------------------

        source_ids = (
            _unique_integers(
                [
                    int(
                        row.get(
                            "source_id"
                        )
                        or row[
                            "knowledge_id"
                        ]
                    )

                    for row in knowledge_rows

                    if row.get(
                        "knowledge_id"
                    )
                    is not None
                ]
            )
        )

        facility_ids = (
            _unique_integers(
                [
                    int(
                        row[
                            "facility_id"
                        ]
                    )

                    for row in facility_rows

                    if row.get(
                        "facility_id"
                    )
                    is not None
                ]
            )
        )

        verified_knowledge_found = bool(
            knowledge_rows
        )

        needs_human_review = (
            priority in {
                "high",
                "critical",
            }
            or special_handling
            or not verified_knowledge_found
            or not bool(facility_rows)
        )

        local_verification_required = (
            local_verification_required
            or needs_human_review
        )

        # ----------------------------------------------------
        # SAVE INSTRUCTION BLOCK
        # ----------------------------------------------------

        work_instructions.append(
            {
                "model_class_id": (
                    model_class_id
                ),

                "class_name": class_name,

                "category_id": category_id,

                "category_name": (
                    category_name
                ),

                "priority": priority,

                **instructions,

                "safety_rule_ids": (
                    safety_rule_ids
                ),

                "source_ids": source_ids,

                "facility_ids": (
                    facility_ids
                ),

                "verified_knowledge_found": (
                    verified_knowledge_found
                ),

                "human_review_required": (
                    needs_human_review
                ),
            }
        )

        # ----------------------------------------------------
        # LIMITATIONS
        # ----------------------------------------------------

        if not knowledge_rows:
            limitations.append(
                (
                    "No verified municipal-employee "
                    f"knowledge was available for "
                    f"{class_name}. Conservative "
                    "worker-safety guidance was used."
                )
            )

        if not facility_rows:
            limitations.append(
                (
                    "No verified local transfer "
                    f"facility was found for "
                    f"{class_name}."
                )
            )

    # --------------------------------------------------------
    # REMOVE REPEATED KNOWLEDGE AND FACILITIES
    # --------------------------------------------------------

    unique_knowledge_rows = (
        _deduplicate_knowledge_rows(
            all_knowledge_rows
        )
    )

    verified_facilities = (
        _deduplicate_facilities(
            all_facility_rows
        )
    )

    limitations.insert(
        0,
        (
            "Gemini was not used. This response was "
            "created from the employee assignment, "
            "YOLO detection, project safety rules "
            "and verified retrieval."
        ),
    )

    limitations = _unique_strings(
        limitations
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    summary = (
        f"Prepared worker guidance for "
        f"{len(work_instructions)} waste class(es) "
        f"under assignment {assignment_id}. "
        f"The overall work priority is "
        f"{overall_priority}."
    )

    # --------------------------------------------------------
    # FINAL STRUCTURED RESPONSE
    # --------------------------------------------------------

    payload: EmployeeAdviceResponse = {
        "mode": "offline_grounded",

        "response_language": (
            response_language
        ),

        "overall_priority": (
            overall_priority
        ),

        "local_verification_required": (
            local_verification_required
        ),

        "employee": {
            "employee_id": int(
                employee[
                    "employee_id"
                ]
            ),

            "user_id": int(
                employee["user_id"]
            ),

            "employee_name": _text(
                employee.get(
                    "employee_name"
                ),
                "Unknown employee",
            ),

            "employee_code": _text(
                employee.get(
                    "employee_code"
                ),
                "Not assigned",
            ),

            "job_title": _text(
                employee.get(
                    "job_title"
                ),
                "Municipal employee",
            ),

            "organization_name": _text(
                employee.get(
                    "organization_name"
                ),
                "Unknown authority",
            ),

            "region_id": (
                int(
                    employee[
                        "region_id"
                    ]
                )

                if employee.get(
                    "region_id"
                )
                is not None

                else None
            ),

            "region_name": (
                _text(
                    employee.get(
                        "region_name"
                    )
                )
                or None
            ),

            "region_type": (
                _text(
                    employee.get(
                        "region_type"
                    )
                )
                or None
            ),
        },

        "assignment": {
            "assignment_id": int(
                assignment[
                    "assignment_id"
                ]
            ),

            "report_id": int(
                assignment[
                    "report_id"
                ]
            ),

            "assignment_status": _text(
                assignment.get(
                    "assignment_status"
                ),
                "assigned",
            ),

            # Database "urgent" becomes
            # response priority "critical".
            "assignment_priority": (
                assignment_priority
            ),

            "assignment_notes": (
                _text(
                    assignment.get(
                        "assignment_notes"
                    )
                )
                or None
            ),

            "report_title": _text(
                assignment.get(
                    "report_title"
                ),
                "Waste cleanup task",
            ),

            "report_description": (
                _text(
                    assignment.get(
                        "report_description"
                    )
                )
                or None
            ),

            "address_text": _text(
                assignment.get(
                    "address_text"
                ),
                "Address not provided",
            ),

            "latitude": _number(
                assignment.get(
                    "latitude"
                )
            ),

            "longitude": _number(
                assignment.get(
                    "longitude"
                )
            ),

            "due_at": _iso(
                assignment.get(
                    "due_at"
                )
            ),
        },

        "detection": {
            "detection_session_id": (
                detection_session_id
            ),

            "request_uuid": _text(
                detection.get(
                    "request_uuid"
                ),
                "unknown-request",
            ),

            "original_filename": _text(
                detection.get(
                    "original_filename"
                ),
                "unknown-file",
            ),

            "model_version": _text(
                detection.get(
                    "version_name"
                ),
                "Unknown model version",
            ),

            "architecture": _text(
                detection.get(
                    "architecture"
                ),
                "Unknown architecture",
            ),

            "detected_objects": [
                {
                    "detected_object_id": (
                        int(
                            row[
                                "detected_object_id"
                            ]
                        )
                    ),

                    "model_class_id": int(
                        row[
                            "model_class_id"
                        ]
                    ),

                    "class_name": _text(
                        row.get(
                            "class_name"
                        ),
                        "Unknown class",
                    ),

                    "display_name": _text(
                        row.get(
                            "display_name"
                        )
                        or row.get(
                            "class_name"
                        ),
                        "Unknown waste",
                    ),

                    "category_id": int(
                        row[
                            "category_id"
                        ]
                    ),

                    "category_code": _text(
                        row.get(
                            "category_code"
                        ),
                        "UNKNOWN",
                    ),

                    "category_name": _text(
                        row.get(
                            "category_name"
                        ),
                        "Unknown category",
                    ),

                    "confidence": float(
                        _number(
                            row.get(
                                "confidence"
                            ),
                            0.0,
                        )
                        or 0.0
                    ),

                    "hazard_level": _text(
                        row.get(
                            "hazard_level"
                        ),
                        "medium",
                    ),

                    "requires_special_handling": (
                        bool(
                            row.get(
                                "requires_special_handling"
                            )
                        )
                    ),
                }

                for row in detected_objects
            ],
        },

        "work_instructions": (
            work_instructions
        ),

        "verified_facilities": (
            verified_facilities
        ),

        "source_list": [
            _format_source(row)

            for row in (
                unique_knowledge_rows
            )
        ],

        "summary": summary,

        "limitations": limitations,

        "disclaimer": (
            "This result is operational decision-support "
            "for municipal waste work. Follow supervisor "
            "instructions, local safety procedures and "
            "facility acceptance rules. Stop work when "
            "a hazard is beyond the employee's training "
            "or available protective equipment."
        ),
    }

    # --------------------------------------------------------
    # VALIDATE RESPONSE
    # --------------------------------------------------------

    validated_payload = (
        validate_employee_advice_response(
            payload
        )
    )

    # --------------------------------------------------------
    # SAVE RESPONSE
    # --------------------------------------------------------

    advice_id = create_employee_advice(
        detection_session_id=(
            detection_session_id
        ),

        priority_level=(
            overall_priority
        ),

        summary=summary,

        response_language=(
            response_language
        ),

        response_payload=(
            validated_payload
        ),

        prompt_version=(
            PROMPT_VERSION
        ),
    )

    # --------------------------------------------------------
    # SAVE KNOWLEDGE AUDIT LINKS
    # --------------------------------------------------------

    save_employee_advice_knowledge_links(
        advice_id=advice_id,

        knowledge_rows=(
            unique_knowledge_rows
        ),
    )

    return {
        "advice_id": advice_id,

        "assignment_id": (
            assignment_id
        ),

        "detection_session_id": (
            detection_session_id
        ),

        "result": (
            validated_payload
        ),
    }