from typing import Any, TypedDict


# ============================================================
# ALLOWED VALUES
# ============================================================

ALLOWED_ADVICE_MODES = {
    "offline_grounded",
    "gemini_grounded",
}

ALLOWED_LANGUAGES = {
    "en",
    "bn",
}

ALLOWED_PRIORITIES = {
    "low",
    "medium",
    "high",
    "critical",
}

ALLOWED_HAZARD_LEVELS = {
    "low",
    "medium",
    "high",
}


# ============================================================
# RESPONSE TYPE DEFINITIONS
# ============================================================

class HouseholdScope(TypedDict):
    user_id: int
    full_name: str
    region_id: int | None
    region_name: str | None
    region_type: str | None


class DetectedWasteItem(TypedDict):
    detected_object_id: int
    model_class_id: int

    class_name: str
    display_name: str

    category_id: int
    category_code: str
    category_name: str

    confidence: float | None

    hazard_level: str
    requires_special_handling: bool


class HouseholdDetection(TypedDict):
    detection_session_id: int
    request_uuid: str
    original_filename: str

    model_version: str
    architecture: str

    detected_objects: list[DetectedWasteItem]


class HouseholdObjectGuidance(TypedDict):
    model_class_id: int
    class_name: str

    category_id: int
    category_name: str

    priority: str

    immediate_actions: list[str]
    segregation_steps: list[str]
    preparation_steps: list[str]
    temporary_storage_steps: list[str]
    disposal_steps: list[str]

    safety_precautions: list[str]
    prohibited_actions: list[str]

    environmental_notes: list[str]
    recycling_opportunities: list[str]

    safety_rule_ids: list[int]
    source_ids: list[int]
    facility_ids: list[int]

    verified_knowledge_found: bool
    human_review_required: bool


class AdviceSource(TypedDict):
    source_id: int
    title: str
    issuing_authority: str
    jurisdiction: str

    page_or_section: str
    last_checked_at: str | None
    source_url: str | None


class HouseholdAdviceResponse(TypedDict):
    mode: str
    response_language: str

    household: HouseholdScope
    detection: HouseholdDetection

    overall_priority: str
    summary: str

    guidance: list[HouseholdObjectGuidance]
    source_list: list[AdviceSource]
    verified_facilities: list[dict[str, Any]]

    limitations: list[str]

    local_verification_required: bool
    disclaimer: str


# ============================================================
# VALIDATION ERROR
# ============================================================

class HouseholdAdviceValidationError(ValueError):
    """Raised when a Household RAG response is invalid."""


# ============================================================
# BASIC VALIDATION HELPERS
# ============================================================

def _require_dictionary(
    value: Any,
    field_name: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise HouseholdAdviceValidationError(
            f"{field_name} must be a dictionary."
        )

    return value


def _require_list(
    value: Any,
    field_name: str,
) -> list[Any]:
    if not isinstance(value, list):
        raise HouseholdAdviceValidationError(
            f"{field_name} must be a list."
        )

    return value


def _require_string(
    value: Any,
    field_name: str,
    allow_empty: bool = False,
) -> str:
    if not isinstance(value, str):
        raise HouseholdAdviceValidationError(
            f"{field_name} must be a string."
        )

    if not allow_empty and not value.strip():
        raise HouseholdAdviceValidationError(
            f"{field_name} cannot be empty."
        )

    return value


def _require_integer(
    value: Any,
    field_name: str,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise HouseholdAdviceValidationError(
            f"{field_name} must be an integer."
        )

    return value


def _require_positive_integer(
    value: Any,
    field_name: str,
) -> int:
    number = _require_integer(
        value,
        field_name,
    )

    if number <= 0:
        raise HouseholdAdviceValidationError(
            f"{field_name} must be greater than zero."
        )

    return number


def _require_number(
    value: Any,
    field_name: str,
) -> float:
    if isinstance(value, bool):
        raise HouseholdAdviceValidationError(
            f"{field_name} must be numeric."
        )

    if not isinstance(value, (int, float)):
        raise HouseholdAdviceValidationError(
            f"{field_name} must be numeric."
        )

    return float(value)


def _require_boolean(
    value: Any,
    field_name: str,
) -> bool:
    if not isinstance(value, bool):
        raise HouseholdAdviceValidationError(
            f"{field_name} must be boolean."
        )

    return value


def _validate_string_list(
    value: Any,
    field_name: str,
) -> list[str]:
    items = _require_list(
        value,
        field_name,
    )

    for index, item in enumerate(items):
        _require_string(
            item,
            f"{field_name}[{index}]",
        )

    return items


def _validate_integer_list(
    value: Any,
    field_name: str,
) -> list[int]:
    items = _require_list(
        value,
        field_name,
    )

    for index, item in enumerate(items):
        _require_positive_integer(
            item,
            f"{field_name}[{index}]",
        )

    return items


# ============================================================
# HOUSEHOLD VALIDATION
# ============================================================

def _validate_household(
    value: Any,
) -> None:
    household = _require_dictionary(
        value,
        "household",
    )

    required_fields = {
        "user_id",
        "full_name",
        "region_id",
        "region_name",
        "region_type",
    }

    missing_fields = (
        required_fields - household.keys()
    )

    if missing_fields:
        raise HouseholdAdviceValidationError(
            "household is missing: "
            + ", ".join(sorted(missing_fields))
        )

    _require_positive_integer(
        household["user_id"],
        "household.user_id",
    )

    _require_string(
        household["full_name"],
        "household.full_name",
    )

    region_id = household["region_id"]

    if region_id is not None:
        _require_positive_integer(
            region_id,
            "household.region_id",
        )

    region_name = household["region_name"]

    if region_name is not None:
        _require_string(
            region_name,
            "household.region_name",
        )

    region_type = household["region_type"]

    if region_type is not None:
        _require_string(
            region_type,
            "household.region_type",
        )


# ============================================================
# DETECTION VALIDATION
# ============================================================

def _validate_detected_object(
    value: Any,
    index: int,
) -> int:
    field_name = (
        f"detection.detected_objects[{index}]"
    )

    detected_object = _require_dictionary(
        value,
        field_name,
    )

    required_fields = {
        "detected_object_id",
        "model_class_id",
        "class_name",
        "display_name",
        "category_id",
        "category_code",
        "category_name",
        "confidence",
        "hazard_level",
        "requires_special_handling",
    }

    missing_fields = (
        required_fields - detected_object.keys()
    )

    if missing_fields:
        raise HouseholdAdviceValidationError(
            f"{field_name} is missing: "
            + ", ".join(sorted(missing_fields))
        )

    _require_positive_integer(
        detected_object["detected_object_id"],
        f"{field_name}.detected_object_id",
    )

    model_class_id = _require_positive_integer(
        detected_object["model_class_id"],
        f"{field_name}.model_class_id",
    )

    _require_string(
        detected_object["class_name"],
        f"{field_name}.class_name",
    )

    _require_string(
        detected_object["display_name"],
        f"{field_name}.display_name",
    )

    _require_positive_integer(
        detected_object["category_id"],
        f"{field_name}.category_id",
    )

    _require_string(
        detected_object["category_code"],
        f"{field_name}.category_code",
    )

    _require_string(
        detected_object["category_name"],
        f"{field_name}.category_name",
    )

    confidence = detected_object["confidence"]

    if confidence is not None:
        confidence_number = _require_number(
            confidence,
            f"{field_name}.confidence",
        )

        if confidence_number < 0 or confidence_number > 1:
            raise HouseholdAdviceValidationError(
                f"{field_name}.confidence must be "
                "between 0 and 1."
            )

    hazard_level = _require_string(
        detected_object["hazard_level"],
        f"{field_name}.hazard_level",
    )

    if hazard_level not in ALLOWED_HAZARD_LEVELS:
        raise HouseholdAdviceValidationError(
            f"{field_name}.hazard_level must be "
            "low, medium or high."
        )

    _require_boolean(
        detected_object["requires_special_handling"],
        (
            f"{field_name}"
            ".requires_special_handling"
        ),
    )

    return model_class_id


def _validate_detection(
    value: Any,
) -> set[int]:
    detection = _require_dictionary(
        value,
        "detection",
    )

    required_fields = {
        "detection_session_id",
        "request_uuid",
        "original_filename",
        "model_version",
        "architecture",
        "detected_objects",
    }

    missing_fields = (
        required_fields - detection.keys()
    )

    if missing_fields:
        raise HouseholdAdviceValidationError(
            "detection is missing: "
            + ", ".join(sorted(missing_fields))
        )

    _require_positive_integer(
        detection["detection_session_id"],
        "detection.detection_session_id",
    )

    _require_string(
        detection["request_uuid"],
        "detection.request_uuid",
    )

    _require_string(
        detection["original_filename"],
        "detection.original_filename",
    )

    _require_string(
        detection["model_version"],
        "detection.model_version",
    )

    _require_string(
        detection["architecture"],
        "detection.architecture",
    )

    detected_objects = _require_list(
        detection["detected_objects"],
        "detection.detected_objects",
    )

    if not detected_objects:
        raise HouseholdAdviceValidationError(
            "detection.detected_objects must contain "
            "at least one detected waste item."
        )

    detected_model_class_ids: set[int] = set()

    for index, detected_object in enumerate(
        detected_objects
    ):
        model_class_id = _validate_detected_object(
            detected_object,
            index,
        )

        detected_model_class_ids.add(
            model_class_id
        )

    return detected_model_class_ids


# ============================================================
# GUIDANCE VALIDATION
# ============================================================

def _validate_guidance(
    value: Any,
    detected_model_class_ids: set[int],
) -> None:
    guidance_items = _require_list(
        value,
        "guidance",
    )

    if not guidance_items:
        raise HouseholdAdviceValidationError(
            "guidance must contain at least one item."
        )

    required_fields = {
        "model_class_id",
        "class_name",
        "category_id",
        "category_name",
        "priority",
        "immediate_actions",
        "segregation_steps",
        "preparation_steps",
        "temporary_storage_steps",
        "disposal_steps",
        "safety_precautions",
        "prohibited_actions",
        "environmental_notes",
        "recycling_opportunities",
        "safety_rule_ids",
        "source_ids",
        "facility_ids",
        "verified_knowledge_found",
        "human_review_required",
    }

    seen_model_class_ids: set[int] = set()

    for index, value_item in enumerate(
        guidance_items
    ):
        field_name = f"guidance[{index}]"

        guidance = _require_dictionary(
            value_item,
            field_name,
        )

        missing_fields = (
            required_fields - guidance.keys()
        )

        if missing_fields:
            raise HouseholdAdviceValidationError(
                f"{field_name} is missing: "
                + ", ".join(sorted(missing_fields))
            )

        model_class_id = _require_positive_integer(
            guidance["model_class_id"],
            f"{field_name}.model_class_id",
        )

        if model_class_id not in detected_model_class_ids:
            raise HouseholdAdviceValidationError(
                f"{field_name}.model_class_id was not "
                "present in the detection result."
            )

        if model_class_id in seen_model_class_ids:
            raise HouseholdAdviceValidationError(
                "Duplicate guidance was found for "
                f"model_class_id {model_class_id}."
            )

        seen_model_class_ids.add(
            model_class_id
        )

        _require_string(
            guidance["class_name"],
            f"{field_name}.class_name",
        )

        _require_positive_integer(
            guidance["category_id"],
            f"{field_name}.category_id",
        )

        _require_string(
            guidance["category_name"],
            f"{field_name}.category_name",
        )

        priority = _require_string(
            guidance["priority"],
            f"{field_name}.priority",
        )

        if priority not in ALLOWED_PRIORITIES:
            raise HouseholdAdviceValidationError(
                f"{field_name}.priority must be low, "
                "medium, high or critical."
            )

        immediate_actions = _validate_string_list(
            guidance["immediate_actions"],
            f"{field_name}.immediate_actions",
        )

        if not immediate_actions:
            raise HouseholdAdviceValidationError(
                f"{field_name}.immediate_actions must "
                "contain at least one action."
            )

        _validate_string_list(
            guidance["segregation_steps"],
            f"{field_name}.segregation_steps",
        )

        _validate_string_list(
            guidance["preparation_steps"],
            f"{field_name}.preparation_steps",
        )

        _validate_string_list(
            guidance["temporary_storage_steps"],
            f"{field_name}.temporary_storage_steps",
        )

        disposal_steps = _validate_string_list(
            guidance["disposal_steps"],
            f"{field_name}.disposal_steps",
        )

        if not disposal_steps:
            raise HouseholdAdviceValidationError(
                f"{field_name}.disposal_steps must "
                "contain at least one step."
            )

        _validate_string_list(
            guidance["safety_precautions"],
            f"{field_name}.safety_precautions",
        )

        _validate_string_list(
            guidance["prohibited_actions"],
            f"{field_name}.prohibited_actions",
        )

        _validate_string_list(
            guidance["environmental_notes"],
            f"{field_name}.environmental_notes",
        )

        _validate_string_list(
            guidance["recycling_opportunities"],
            f"{field_name}.recycling_opportunities",
        )

        _validate_integer_list(
            guidance["safety_rule_ids"],
            f"{field_name}.safety_rule_ids",
        )

        _validate_integer_list(
            guidance["source_ids"],
            f"{field_name}.source_ids",
        )

        _validate_integer_list(
            guidance["facility_ids"],
            f"{field_name}.facility_ids",
        )

        _require_boolean(
            guidance["verified_knowledge_found"],
            (
                f"{field_name}"
                ".verified_knowledge_found"
            ),
        )

        _require_boolean(
            guidance["human_review_required"],
            (
                f"{field_name}"
                ".human_review_required"
            ),
        )


# ============================================================
# SOURCE VALIDATION
# ============================================================

def _validate_sources(
    value: Any,
) -> None:
    sources = _require_list(
        value,
        "source_list",
    )

    required_fields = {
        "source_id",
        "title",
        "issuing_authority",
        "jurisdiction",
        "page_or_section",
        "last_checked_at",
        "source_url",
    }

    seen_source_ids: set[int] = set()

    for index, value_item in enumerate(sources):
        field_name = f"source_list[{index}]"

        source = _require_dictionary(
            value_item,
            field_name,
        )

        missing_fields = (
            required_fields - source.keys()
        )

        if missing_fields:
            raise HouseholdAdviceValidationError(
                f"{field_name} is missing: "
                + ", ".join(sorted(missing_fields))
            )

        source_id = _require_positive_integer(
            source["source_id"],
            f"{field_name}.source_id",
        )

        if source_id in seen_source_ids:
            raise HouseholdAdviceValidationError(
                f"Duplicate source_id found: {source_id}"
            )

        seen_source_ids.add(
            source_id
        )

        _require_string(
            source["title"],
            f"{field_name}.title",
        )

        _require_string(
            source["issuing_authority"],
            f"{field_name}.issuing_authority",
        )

        _require_string(
            source["jurisdiction"],
            f"{field_name}.jurisdiction",
        )

        _require_string(
            source["page_or_section"],
            f"{field_name}.page_or_section",
        )

        last_checked_at = source[
            "last_checked_at"
        ]

        if last_checked_at is not None:
            _require_string(
                last_checked_at,
                f"{field_name}.last_checked_at",
            )

        source_url = source["source_url"]

        if source_url is not None:
            _require_string(
                source_url,
                f"{field_name}.source_url",
            )


# ============================================================
# FACILITY VALIDATION
# ============================================================

def _validate_facilities(
    value: Any,
) -> None:
    facilities = _require_list(
        value,
        "verified_facilities",
    )

    seen_facility_ids: set[int] = set()

    for index, value_item in enumerate(
        facilities
    ):
        field_name = (
            f"verified_facilities[{index}]"
        )

        facility = _require_dictionary(
            value_item,
            field_name,
        )

        required_fields = {
            "facility_id",
            "region_id",
            "facility_name",
            "facility_type",
            "address_text",
        }

        missing_fields = (
            required_fields - facility.keys()
        )

        if missing_fields:
            raise HouseholdAdviceValidationError(
                f"{field_name} is missing: "
                + ", ".join(sorted(missing_fields))
            )

        facility_id = _require_positive_integer(
            facility["facility_id"],
            f"{field_name}.facility_id",
        )

        if facility_id in seen_facility_ids:
            raise HouseholdAdviceValidationError(
                "Duplicate facility_id found: "
                f"{facility_id}"
            )

        seen_facility_ids.add(
            facility_id
        )

        _require_positive_integer(
            facility["region_id"],
            f"{field_name}.region_id",
        )

        _require_string(
            facility["facility_name"],
            f"{field_name}.facility_name",
        )

        _require_string(
            facility["facility_type"],
            f"{field_name}.facility_type",
        )

        _require_string(
            facility["address_text"],
            f"{field_name}.address_text",
        )


# ============================================================
# COMPLETE RESPONSE VALIDATION
# ============================================================

def validate_household_advice_response(
    value: Any,
) -> HouseholdAdviceResponse:
    """
    Validate the complete Household RAG response.

    This validator will be used for:
    - offline advice now;
    - Gemini structured responses later.
    """

    response = _require_dictionary(
        value,
        "household advice response",
    )

    required_fields = {
        "mode",
        "response_language",
        "household",
        "detection",
        "overall_priority",
        "summary",
        "guidance",
        "source_list",
        "verified_facilities",
        "limitations",
        "local_verification_required",
        "disclaimer",
    }

    missing_fields = (
        required_fields - response.keys()
    )

    if missing_fields:
        raise HouseholdAdviceValidationError(
            "Household advice response is missing: "
            + ", ".join(sorted(missing_fields))
        )

    mode = _require_string(
        response["mode"],
        "mode",
    )

    if mode not in ALLOWED_ADVICE_MODES:
        raise HouseholdAdviceValidationError(
            "mode must be offline_grounded "
            "or gemini_grounded."
        )

    language = _require_string(
        response["response_language"],
        "response_language",
    )

    if language not in ALLOWED_LANGUAGES:
        raise HouseholdAdviceValidationError(
            "response_language must be 'en' or 'bn'."
        )

    priority = _require_string(
        response["overall_priority"],
        "overall_priority",
    )

    if priority not in ALLOWED_PRIORITIES:
        raise HouseholdAdviceValidationError(
            "overall_priority must be low, medium, "
            "high or critical."
        )

    _require_string(
        response["summary"],
        "summary",
    )

    _validate_household(
        response["household"]
    )

    detected_model_class_ids = (
        _validate_detection(
            response["detection"]
        )
    )

    _validate_guidance(
        response["guidance"],
        detected_model_class_ids,
    )

    _validate_sources(
        response["source_list"]
    )

    _validate_facilities(
        response["verified_facilities"]
    )

    _validate_string_list(
        response["limitations"],
        "limitations",
    )

    _require_boolean(
        response["local_verification_required"],
        "local_verification_required",
    )

    _require_string(
        response["disclaimer"],
        "disclaimer",
    )

    return response  # type: ignore[return-value]