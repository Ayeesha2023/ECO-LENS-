from typing import Any, TypedDict


# ============================================================
# ALLOWED VALUES
# ============================================================

ALLOWED_PRIORITIES = {
    "low",
    "medium",
    "high",
    "critical",
}

ALLOWED_LANGUAGES = {
    "en",
    "bn",
}

ALLOWED_MODES = {
    "offline_grounded",
    "gemini_grounded",
}


# ============================================================
# TYPED RESPONSE STRUCTURES
# ============================================================

class EmployeeInformation(TypedDict):
    employee_id: int
    user_id: int
    employee_name: str
    employee_code: str
    job_title: str
    organization_name: str
    region_id: int | None
    region_name: str | None
    region_type: str | None


class EmployeeAssignmentInformation(TypedDict):
    assignment_id: int
    report_id: int
    assignment_status: str
    assignment_priority: str
    assignment_notes: str | None
    report_title: str
    report_description: str | None
    address_text: str
    latitude: float | None
    longitude: float | None
    due_at: str | None


class EmployeeDetectedObject(TypedDict):
    detected_object_id: int
    model_class_id: int
    class_name: str
    display_name: str
    category_id: int
    category_code: str
    category_name: str
    confidence: float
    hazard_level: str
    requires_special_handling: bool


class EmployeeDetectionInformation(TypedDict):
    detection_session_id: int
    request_uuid: str
    original_filename: str
    model_version: str
    architecture: str
    detected_objects: list[EmployeeDetectedObject]


class EmployeeWorkInstruction(TypedDict):
    model_class_id: int
    class_name: str
    category_id: int
    category_name: str
    priority: str

    ppe_requirements: list[str]
    site_preparation_steps: list[str]
    collection_steps: list[str]
    segregation_steps: list[str]
    handling_precautions: list[str]
    temporary_storage_steps: list[str]
    transport_steps: list[str]
    prohibited_actions: list[str]
    emergency_actions: list[str]
    reporting_steps: list[str]

    safety_rule_ids: list[int]
    source_ids: list[int]
    facility_ids: list[int]

    verified_knowledge_found: bool
    human_review_required: bool


class EmployeeVerifiedFacility(TypedDict, total=False):
    facility_id: int
    facility_name: str
    facility_type: str
    region_id: int
    region_name: str
    address_text: str
    latitude: float
    longitude: float
    phone: str
    email: str
    opening_hours: str
    acceptance_notes: str


class EmployeeKnowledgeSource(TypedDict, total=False):
    knowledge_id: int
    source_id: int
    source_title: str
    source_organization: str
    source_url: str
    topic: str
    retrieval_method: str
    retrieval_score: float


class EmployeeAdviceResponse(TypedDict):
    mode: str
    response_language: str
    overall_priority: str
    local_verification_required: bool

    employee: EmployeeInformation
    assignment: EmployeeAssignmentInformation
    detection: EmployeeDetectionInformation

    work_instructions: list[EmployeeWorkInstruction]
    verified_facilities: list[EmployeeVerifiedFacility]
    source_list: list[EmployeeKnowledgeSource]

    summary: str
    limitations: list[str]
    disclaimer: str


# ============================================================
# GENERAL VALIDATION HELPERS
# ============================================================

def _require_dictionary(
    value: Any,
    field_name: str,
) -> dict[str, Any]:
    """Confirm that a value is a dictionary."""

    if not isinstance(value, dict):
        raise ValueError(
            f"{field_name} must be a JSON object."
        )

    return value


def _require_list(
    value: Any,
    field_name: str,
) -> list[Any]:
    """Confirm that a value is a list."""

    if not isinstance(value, list):
        raise ValueError(
            f"{field_name} must be a list."
        )

    return value


def _require_string(
    value: Any,
    field_name: str,
    allow_empty: bool = False,
) -> str:
    """Confirm that a value is a string."""

    if not isinstance(value, str):
        raise ValueError(
            f"{field_name} must be a string."
        )

    cleaned_value = value.strip()

    if not allow_empty and not cleaned_value:
        raise ValueError(
            f"{field_name} cannot be empty."
        )

    return cleaned_value


def _require_integer(
    value: Any,
    field_name: str,
    allow_none: bool = False,
) -> int | None:
    """Confirm that a value is an integer."""

    if value is None and allow_none:
        return None

    if isinstance(value, bool):
        raise ValueError(
            f"{field_name} must be an integer."
        )

    if not isinstance(value, int):
        raise ValueError(
            f"{field_name} must be an integer."
        )

    return value


def _require_number(
    value: Any,
    field_name: str,
    allow_none: bool = False,
) -> float | int | None:
    """Confirm that a value is numeric."""

    if value is None and allow_none:
        return None

    if isinstance(value, bool):
        raise ValueError(
            f"{field_name} must be a number."
        )

    if not isinstance(value, (int, float)):
        raise ValueError(
            f"{field_name} must be a number."
        )

    return value


def _require_boolean(
    value: Any,
    field_name: str,
) -> bool:
    """Confirm that a value is a Boolean."""

    if not isinstance(value, bool):
        raise ValueError(
            f"{field_name} must be true or false."
        )

    return value


def _validate_string_list(
    value: Any,
    field_name: str,
) -> list[str]:
    """Validate a list containing strings."""

    values = _require_list(
        value,
        field_name,
    )

    for index, item in enumerate(values):
        _require_string(
            item,
            f"{field_name}[{index}]",
        )

    return values


def _validate_integer_list(
    value: Any,
    field_name: str,
) -> list[int]:
    """Validate a list containing integer IDs."""

    values = _require_list(
        value,
        field_name,
    )

    for index, item in enumerate(values):
        _require_integer(
            item,
            f"{field_name}[{index}]",
        )

    return values


# ============================================================
# EMPLOYEE INFORMATION VALIDATION
# ============================================================

def _validate_employee_information(
    employee: Any,
) -> None:
    employee = _require_dictionary(
        employee,
        "employee",
    )

    required_fields = {
        "employee_id",
        "user_id",
        "employee_name",
        "employee_code",
        "job_title",
        "organization_name",
        "region_id",
        "region_name",
        "region_type",
    }

    missing_fields = required_fields - employee.keys()

    if missing_fields:
        raise ValueError(
            "employee is missing fields: "
            + ", ".join(sorted(missing_fields))
        )

    _require_integer(
        employee["employee_id"],
        "employee.employee_id",
    )

    _require_integer(
        employee["user_id"],
        "employee.user_id",
    )

    _require_string(
        employee["employee_name"],
        "employee.employee_name",
    )

    _require_string(
        employee["employee_code"],
        "employee.employee_code",
    )

    _require_string(
        employee["job_title"],
        "employee.job_title",
    )

    _require_string(
        employee["organization_name"],
        "employee.organization_name",
    )

    _require_integer(
        employee["region_id"],
        "employee.region_id",
        allow_none=True,
    )

    if employee["region_name"] is not None:
        _require_string(
            employee["region_name"],
            "employee.region_name",
        )

    if employee["region_type"] is not None:
        _require_string(
            employee["region_type"],
            "employee.region_type",
        )


# ============================================================
# ASSIGNMENT VALIDATION
# ============================================================

def _validate_assignment_information(
    assignment: Any,
) -> None:
    assignment = _require_dictionary(
        assignment,
        "assignment",
    )

    required_fields = {
        "assignment_id",
        "report_id",
        "assignment_status",
        "assignment_priority",
        "assignment_notes",
        "report_title",
        "report_description",
        "address_text",
        "latitude",
        "longitude",
        "due_at",
    }

    missing_fields = required_fields - assignment.keys()

    if missing_fields:
        raise ValueError(
            "assignment is missing fields: "
            + ", ".join(sorted(missing_fields))
        )

    _require_integer(
        assignment["assignment_id"],
        "assignment.assignment_id",
    )

    _require_integer(
        assignment["report_id"],
        "assignment.report_id",
    )

    _require_string(
        assignment["assignment_status"],
        "assignment.assignment_status",
    )

    priority = _require_string(
        assignment["assignment_priority"],
        "assignment.assignment_priority",
    )

    if priority not in ALLOWED_PRIORITIES:
        raise ValueError(
            "assignment.assignment_priority must be "
            "low, medium, high or critical."
        )

    if assignment["assignment_notes"] is not None:
        _require_string(
            assignment["assignment_notes"],
            "assignment.assignment_notes",
            allow_empty=True,
        )

    _require_string(
        assignment["report_title"],
        "assignment.report_title",
    )

    if assignment["report_description"] is not None:
        _require_string(
            assignment["report_description"],
            "assignment.report_description",
            allow_empty=True,
        )

    _require_string(
        assignment["address_text"],
        "assignment.address_text",
    )

    _require_number(
        assignment["latitude"],
        "assignment.latitude",
        allow_none=True,
    )

    _require_number(
        assignment["longitude"],
        "assignment.longitude",
        allow_none=True,
    )

    if assignment["due_at"] is not None:
        _require_string(
            assignment["due_at"],
            "assignment.due_at",
        )


# ============================================================
# DETECTION VALIDATION
# ============================================================

def _validate_detected_object(
    detected_object: Any,
    index: int,
) -> None:
    field_name = (
        f"detection.detected_objects[{index}]"
    )

    detected_object = _require_dictionary(
        detected_object,
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
        raise ValueError(
            f"{field_name} is missing fields: "
            + ", ".join(sorted(missing_fields))
        )

    _require_integer(
        detected_object["detected_object_id"],
        f"{field_name}.detected_object_id",
    )

    _require_integer(
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

    _require_integer(
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

    confidence = _require_number(
        detected_object["confidence"],
        f"{field_name}.confidence",
    )

    if confidence is not None and not 0 <= confidence <= 1:
        raise ValueError(
            f"{field_name}.confidence must be "
            "between 0 and 1."
        )

    _require_string(
        detected_object["hazard_level"],
        f"{field_name}.hazard_level",
    )

    _require_boolean(
        detected_object[
            "requires_special_handling"
        ],
        (
            f"{field_name}."
            "requires_special_handling"
        ),
    )


def _validate_detection_information(
    detection: Any,
) -> None:
    detection = _require_dictionary(
        detection,
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

    missing_fields = required_fields - detection.keys()

    if missing_fields:
        raise ValueError(
            "detection is missing fields: "
            + ", ".join(sorted(missing_fields))
        )

    _require_integer(
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
        raise ValueError(
            "detection.detected_objects cannot be empty."
        )

    for index, detected_object in enumerate(
        detected_objects
    ):
        _validate_detected_object(
            detected_object,
            index,
        )


# ============================================================
# WORK INSTRUCTION VALIDATION
# ============================================================

def _validate_work_instruction(
    instruction: Any,
    index: int,
) -> None:
    field_name = f"work_instructions[{index}]"

    instruction = _require_dictionary(
        instruction,
        field_name,
    )

    required_fields = {
        "model_class_id",
        "class_name",
        "category_id",
        "category_name",
        "priority",
        "ppe_requirements",
        "site_preparation_steps",
        "collection_steps",
        "segregation_steps",
        "handling_precautions",
        "temporary_storage_steps",
        "transport_steps",
        "prohibited_actions",
        "emergency_actions",
        "reporting_steps",
        "safety_rule_ids",
        "source_ids",
        "facility_ids",
        "verified_knowledge_found",
        "human_review_required",
    }

    missing_fields = (
        required_fields - instruction.keys()
    )

    if missing_fields:
        raise ValueError(
            f"{field_name} is missing fields: "
            + ", ".join(sorted(missing_fields))
        )

    _require_integer(
        instruction["model_class_id"],
        f"{field_name}.model_class_id",
    )

    _require_string(
        instruction["class_name"],
        f"{field_name}.class_name",
    )

    _require_integer(
        instruction["category_id"],
        f"{field_name}.category_id",
    )

    _require_string(
        instruction["category_name"],
        f"{field_name}.category_name",
    )

    priority = _require_string(
        instruction["priority"],
        f"{field_name}.priority",
    )

    if priority not in ALLOWED_PRIORITIES:
        raise ValueError(
            f"{field_name}.priority must be "
            "low, medium, high or critical."
        )

    string_list_fields = {
        "ppe_requirements",
        "site_preparation_steps",
        "collection_steps",
        "segregation_steps",
        "handling_precautions",
        "temporary_storage_steps",
        "transport_steps",
        "prohibited_actions",
        "emergency_actions",
        "reporting_steps",
    }

    for list_field in string_list_fields:
        _validate_string_list(
            instruction[list_field],
            f"{field_name}.{list_field}",
        )

    integer_list_fields = {
        "safety_rule_ids",
        "source_ids",
        "facility_ids",
    }

    for list_field in integer_list_fields:
        _validate_integer_list(
            instruction[list_field],
            f"{field_name}.{list_field}",
        )

    _require_boolean(
        instruction["verified_knowledge_found"],
        (
            f"{field_name}."
            "verified_knowledge_found"
        ),
    )

    _require_boolean(
        instruction["human_review_required"],
        (
            f"{field_name}."
            "human_review_required"
        ),
    )


# ============================================================
# FINAL EMPLOYEE RESPONSE VALIDATOR
# ============================================================

def validate_employee_advice_response(
    payload: Any,
) -> EmployeeAdviceResponse:
    """
    Validate the complete Employee RAG response.

    The validated payload is returned unchanged.
    """

    payload = _require_dictionary(
        payload,
        "employee advice response",
    )

    required_fields = {
        "mode",
        "response_language",
        "overall_priority",
        "local_verification_required",
        "employee",
        "assignment",
        "detection",
        "work_instructions",
        "verified_facilities",
        "source_list",
        "summary",
        "limitations",
        "disclaimer",
    }

    missing_fields = required_fields - payload.keys()

    if missing_fields:
        raise ValueError(
            "Employee advice response is missing fields: "
            + ", ".join(sorted(missing_fields))
        )

    mode = _require_string(
        payload["mode"],
        "mode",
    )

    if mode not in ALLOWED_MODES:
        raise ValueError(
            "mode must be offline_grounded "
            "or gemini_grounded."
        )

    response_language = _require_string(
        payload["response_language"],
        "response_language",
    )

    if response_language not in ALLOWED_LANGUAGES:
        raise ValueError(
            "response_language must be 'en' or 'bn'."
        )

    overall_priority = _require_string(
        payload["overall_priority"],
        "overall_priority",
    )

    if overall_priority not in ALLOWED_PRIORITIES:
        raise ValueError(
            "overall_priority must be low, medium, "
            "high or critical."
        )

    _require_boolean(
        payload["local_verification_required"],
        "local_verification_required",
    )

    _validate_employee_information(
        payload["employee"]
    )

    _validate_assignment_information(
        payload["assignment"]
    )

    _validate_detection_information(
        payload["detection"]
    )

    work_instructions = _require_list(
        payload["work_instructions"],
        "work_instructions",
    )

    if not work_instructions:
        raise ValueError(
            "work_instructions cannot be empty."
        )

    for index, instruction in enumerate(
        work_instructions
    ):
        _validate_work_instruction(
            instruction,
            index,
        )

    verified_facilities = _require_list(
        payload["verified_facilities"],
        "verified_facilities",
    )

    for index, facility in enumerate(
        verified_facilities
    ):
        _require_dictionary(
            facility,
            f"verified_facilities[{index}]",
        )

    source_list = _require_list(
        payload["source_list"],
        "source_list",
    )

    for index, source in enumerate(source_list):
        _require_dictionary(
            source,
            f"source_list[{index}]",
        )

    _require_string(
        payload["summary"],
        "summary",
    )

    _validate_string_list(
        payload["limitations"],
        "limitations",
    )

    _require_string(
        payload["disclaimer"],
        "disclaimer",
    )

    return payload  # type: ignore[return-value]