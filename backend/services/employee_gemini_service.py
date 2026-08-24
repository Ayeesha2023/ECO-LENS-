import json
from typing import Any

from prompts.employee_prompt import (
    build_employee_detailed_prompt,
)
from repositories.employee_repository import (
    get_employee_advice_by_id,
)
from services.gemini_service import (
    DEFAULT_MODEL,
    generate_grounded_json,
)


EMPLOYEE_GEMINI_PROMPT_VERSION = (
    "employee-gemini-detailed-1.0"
)

VALID_PRIORITIES = {
    "low",
    "medium",
    "high",
    "critical",
}


def _parse_saved_json(
    value: Any,
) -> Any:
    """Convert stored MySQL JSON text into Python data."""

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


def _validate_rag_result(
    rag_result: Any,
) -> dict[str, Any]:
    """
    Confirm that the saved advice contains the normal Employee
    RAG result and at least one detected waste class.
    """

    if not isinstance(
        rag_result,
        dict,
    ):
        raise ValueError(
            "The saved Employee RAG guidance is unavailable. "
            "Run the waste scan and basic guidance again."
        )

    detection = rag_result.get(
        "detection"
    )

    detected_objects = (
        detection.get(
            "detected_objects"
        )
        if isinstance(
            detection,
            dict,
        )
        else None
    )

    if not isinstance(
        detected_objects,
        list,
    ) or not detected_objects:
        raise ValueError(
            "No waste class could be detected from this image. "
            "Please upload a clearer image where the waste objects "
            "are clearly visible and try again."
        )

    work_instructions = rag_result.get(
        "work_instructions"
    )

    if not isinstance(
        work_instructions,
        list,
    ) or not work_instructions:
        raise ValueError(
            "Detailed guidance cannot be generated because the "
            "Employee RAG result contains no worker instructions. "
            "Run the basic guidance again first."
        )

    return rag_result


def _validate_gemini_result(
    result: Any,
) -> dict[str, Any]:
    """Validate the minimum structure required by the frontend."""

    if not isinstance(
        result,
        dict,
    ):
        raise ValueError(
            "Gemini Employee guidance must be a JSON object."
        )

    guidance = result.get(
        "guidance"
    )

    if not isinstance(
        guidance,
        list,
    ) or not guidance:
        raise ValueError(
            "Gemini returned no detailed Employee guidance."
        )

    priority = str(
        result.get(
            "overall_priority",
            "medium",
        )
    ).strip().lower()

    if priority not in VALID_PRIORITIES:
        priority = "medium"

    result[
        "overall_priority"
    ] = priority

    result[
        "mode"
    ] = "gemini_grounded_employee"

    if not result.get(
        "summary"
    ):
        result[
            "summary"
        ] = (
            "EcoLens prepared more detailed worker guidance "
            "from the existing Employee RAG result."
        )

    if (
        "local_verification_required"
        not in result
    ):
        result[
            "local_verification_required"
        ] = True

    if not result.get(
        "disclaimer"
    ):
        result[
            "disclaimer"
        ] = (
            "Guidance is based on the existing EcoLens Employee "
            "RAG result and must be used with supervisor and local "
            "safety procedures."
        )

    return result


def generate_employee_detailed_guidance(
    *,
    employee_id: int,
    advice_id: int,
    response_language: str = "en",
) -> dict[str, Any]:
    """
    Generate optional Gemini-expanded Employee guidance.

    The existing saved Employee RAG result is loaded from the
    database first. Gemini receives that grounded result, including
    the YOLO classes, worker instructions, verified facilities and
    source list. Gemini does not rerun detection or replace RAG.
    """

    if employee_id <= 0:
        raise ValueError(
            "employee_id must be greater than zero."
        )

    if advice_id <= 0:
        raise ValueError(
            "advice_id must be greater than zero."
        )

    response_language = (
        str(response_language)
        .strip()
        .lower()
    )

    if response_language not in {
        "en",
        "bn",
    }:
        raise ValueError(
            "response_language must be 'en' or 'bn'."
        )

    advice = get_employee_advice_by_id(
        advice_id=advice_id,
        employee_id=employee_id,
    )

    if advice is None:
        raise ValueError(
            "Employee RAG guidance was not found, or it does "
            "not belong to this employee."
        )

    rag_result = _validate_rag_result(
        _parse_saved_json(
            advice.get(
                "response_json"
            )
        )
    )

    prompt_context = {
        "advice_id": int(
            advice["advice_id"]
        ),
        "detection_session_id": int(
            advice[
                "detection_session_id"
            ]
        ),
        "assignment_id": int(
            advice["assignment_id"]
        ),
        "assignment_status": advice.get(
            "assignment_status"
        ),
        "assignment_priority": advice.get(
            "assignment_priority"
        ),
        "report_title": advice.get(
            "report_title"
        ),
        "address_text": advice.get(
            "address_text"
        ),
        "employee_rag_result": rag_result,
    }

    prompt = build_employee_detailed_prompt(
        rag_result=prompt_context,
        response_language=(
            response_language
        ),
    )

    result = generate_grounded_json(
        prompt=prompt,
        model=DEFAULT_MODEL,
    )

    result = _validate_gemini_result(
        result
    )

    return {
        "advice_id": advice_id,
        "assignment_id": int(
            advice["assignment_id"]
        ),
        "detection_session_id": int(
            advice[
                "detection_session_id"
            ]
        ),
        "response_language": (
            response_language
        ),
        "gemini_model": DEFAULT_MODEL,
        "prompt_version": (
            EMPLOYEE_GEMINI_PROMPT_VERSION
        ),
        "result": result,
    }
