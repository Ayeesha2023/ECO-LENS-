import json
import os

from datetime import (
    date,
    datetime,
)

from decimal import Decimal
from typing import Any

import mysql.connector

from flask import (
    Blueprint,
    jsonify,
    request,
)

from dotenv import load_dotenv


from repositories.household_repository import (
    get_household_advice_by_id,
    get_household_advice_history,
)


from services.household_rag_service import (
    generate_household_advice_offline,
)


from services.gemini_service import (
    generate_grounded_json,
)


from prompts.household_chat_prompt import (
    build_household_chat_prompt,
)


from prompts.household_prompt import (
    build_household_prompt,
)


from services.household_chat_service import (
    build_household_chat_context,
)


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.6-flash",
)


HOUSEHOLD_GEMINI_PROMPT_VERSION = (
    "household-rag-gemini-1.0"
)


HOUSEHOLD_CHAT_PROMPT_VERSION = (
    "household-chat-gemini-1.0"
)


HOUSEHOLD_INITIAL_GEMINI_SCHEMA = {
    "type": "object",

    "properties": {
        "mode": {
            "type": "string",
        },

        "summary": {
            "type": "string",
        },

        "overall_priority": {
            "type": "string",
            "enum": [
                "low",
                "medium",
                "high",
                "critical",
            ],
        },

        "guidance": {
            "type": "array",

            "items": {
                "type": "object",

                "properties": {
                    "model_class_id": {
                        "type": "integer",
                    },

                    "class_name": {
                        "type": "string",
                    },

                    "display_name": {
                        "type": "string",
                    },

                    "category_name": {
                        "type": "string",
                    },

                    "priority": {
                        "type": "string",
                        "enum": [
                            "low",
                            "medium",
                            "high",
                            "critical",
                        ],
                    },

                    "overview": {
                        "type": "string",
                    },

                    "immediate_actions": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                    },

                    "segregation_steps": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                    },

                    "preparation_steps": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                    },

                    "temporary_storage_steps": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                    },

                    "disposal_steps": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                    },

                    "safety_precautions": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                    },

                    "prohibited_actions": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                    },

                    "recycling_opportunities": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                    },

                    "benefits_of_proper_disposal": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                    },

                    "harms_of_improper_disposal": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                    },

                    "environmental_notes": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                    },
                },

                "required": [
                    "model_class_id",
                    "class_name",
                    "display_name",
                    "category_name",
                    "priority",
                    "overview",
                    "immediate_actions",
                    "segregation_steps",
                    "preparation_steps",
                    "temporary_storage_steps",
                    "disposal_steps",
                    "safety_precautions",
                    "prohibited_actions",
                    "recycling_opportunities",
                    "benefits_of_proper_disposal",
                    "harms_of_improper_disposal",
                    "environmental_notes",
                ],
            },
        },

        "local_verification_required": {
            "type": "boolean",
        },

        "disclaimer": {
            "type": "string",
        },
    },

    "required": [
        "mode",
        "summary",
        "overall_priority",
        "guidance",
        "local_verification_required",
        "disclaimer",
    ],
}


# ============================================================
# BLUEPRINT
# ============================================================

household_bp = Blueprint(
    "household",
    __name__,
    url_prefix="/api/household",
)


# ============================================================
# DATABASE
# ============================================================

def _get_connection():

    return mysql.connector.connect(

        host=os.getenv(
            "DB_HOST",
            "127.0.0.1",
        ),

        port=int(
            os.getenv(
                "DB_PORT",
                "3306",
            )
        ),

        user=os.getenv(
            "DB_USER",
            "root",
        ),

        password=os.getenv(
            "DB_PASSWORD",
            "",
        ),

        database=os.getenv(
            "DB_NAME",
            "eco-lens_db",
        ),

        autocommit=False,
    )


# ============================================================
# GENERAL HELPERS
# ============================================================

def _json_safe_value(
    value: Any,
) -> Any:

    """
    Convert values returned by MySQL into JSON-safe values.
    """

    if isinstance(
        value,
        Decimal,
    ):

        return float(
            value
        )


    if isinstance(
        value,
        (
            date,
            datetime,
        ),
    ):

        return value.isoformat()


    if isinstance(
        value,
        dict,
    ):

        return {

            key:
                _json_safe_value(
                    item
                )

            for key, item
            in value.items()
        }


    if isinstance(
        value,
        (
            list,
            tuple,
        ),
    ):

        return [

            _json_safe_value(
                item
            )

            for item
            in value
        ]


    return value


def _parse_saved_json(
    value: Any,
) -> Any:

    """
    Convert stored MySQL JSON into Python values.
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


def _validate_positive_integer(
    value: Any,
    field_name: str,
) -> int:

    """
    Validate and return a positive integer.
    """

    if isinstance(
        value,
        bool,
    ):

        raise ValueError(
            f"{field_name} must be a positive integer."
        )


    try:

        number = int(
            value
        )


    except (
        TypeError,
        ValueError,
    ) as exc:

        raise ValueError(
            f"{field_name} must be a positive integer."
        ) from exc


    if number <= 0:

        raise ValueError(
            f"{field_name} must be greater than zero."
        )


    return number


def _parse_limit(
    value: Any,
    default: int = 20,
    maximum: int = 100,
) -> int:

    """
    Validate advice-history limit.
    """

    if value is None:

        return default


    limit = (
        _validate_positive_integer(
            value,
            "limit",
        )
    )


    return min(
        limit,
        maximum,
    )


def _error_response(
    message: str,
    status_code: int,
):

    """
    Return errors using one consistent JSON format.
    """

    return jsonify(
        {
            "success": False,
            "error": message,
        }
    ), status_code


# ============================================================
# GEMINI PROMPT
# ============================================================

def _build_household_gemini_prompt(
    rag_result: dict[str, Any],
    response_language: str,
) -> str:

    """
    Build a grounded Gemini prompt.

    IMPORTANT:
    Gemini receives the information already retrieved by
    EcoLens RAG. Gemini is not used as the original source
    of waste-management facts.
    """

    safe_context = (
        _json_safe_value(
            rag_result
        )
    )


    context_json = json.dumps(
        safe_context,
        ensure_ascii=False,
        indent=2,
    )


    if response_language == "bn":

        language_instruction = (
            "Write all user-facing guidance in clear Bangla. "
            "Keep JSON property names in English."
        )

    else:

        language_instruction = (
            "Write all user-facing guidance in clear, simple English."
        )


    return f"""
You are the household waste-disposal assistant inside ECO-LENS,
a smart waste-management application for Bangladesh.

A YOLO waste detector has already analysed the user's image.

After detection, ECO-LENS RAG retrieved the information shown
inside RAG_CONTEXT below.

Your job is NOT to independently decide waste-management facts.

Your job is to transform the supplied RAG information into
clear, detailed, practical household disposal guidance.

============================================================
STRICT GROUNDING RULES
============================================================

1. Use the RAG_CONTEXT as the factual source.

2. Do NOT invent:
   - disposal facilities
   - recycling centres
   - addresses
   - phone numbers
   - Bangladesh laws
   - government programmes
   - municipal services
   - collection schedules
   - safety claims
   - environmental statistics

3. If a verified facility is not provided in RAG_CONTEXT,
   do not name one.

4. If information is unavailable, clearly say that verified
   local information is unavailable.

5. Never contradict a safety rule contained in RAG_CONTEXT.

6. Never remove an important warning or prohibited action
   contained in RAG_CONTEXT.

7. Do not change the detected waste class.

8. Give practical household instructions, not instructions
   intended for industrial waste workers.

9. Keep dangerous or hazardous waste advice cautious.

10. {language_instruction}

============================================================
WHAT THE USER NEEDS
============================================================

For every detected waste class, explain:

- what the detected item is
- what the user should do immediately
- how to separate it from other waste
- whether any preparation is required
- how to store it temporarily
- how it should be disposed of or transferred
- important safety precautions
- actions the user must NOT do
- recycling or recovery possibilities
- why incorrect disposal can be harmful

Make the guidance detailed enough to be genuinely useful,
but easy for an ordinary household user to understand.

============================================================
OUTPUT FORMAT
============================================================

Return ONLY valid JSON.

Do not add Markdown before or after the JSON.

Use exactly this overall structure:

{{
    "mode": "gemini_grounded",

    "summary": "A short overall explanation.",

    "overall_priority": "low | medium | high | critical",

    "guidance": [
        {{
            "model_class_id": 1,

            "class_name": "Detected waste class",

            "display_name": "Human readable waste name",

            "category_name": "Waste category",

            "priority": "low | medium | high | critical",

            "overview": "Easy explanation of what was detected.",

            "immediate_actions": [
                "step"
            ],

            "segregation_steps": [
                "step"
            ],

            "preparation_steps": [
                "step"
            ],

            "temporary_storage_steps": [
                "step"
            ],

            "disposal_steps": [
                "step"
            ],

            "safety_precautions": [
                "step"
            ],

            "prohibited_actions": [
                "step"
            ],

            "recycling_opportunities": [
                "step"
            ],

            "environmental_notes": [
                "step"
            ]
        }}
    ],

    "local_verification_required": true,

    "disclaimer":
        "Guidance is based on EcoLens retrieved knowledge. Local disposal availability should be verified when necessary."
}}

============================================================
RAG_CONTEXT
============================================================

{context_json}

============================================================
FINAL INSTRUCTION
============================================================

Generate the household disposal guidance now.

Return valid JSON only.
"""


# ============================================================
# GEMINI RESPONSE VALIDATION
# ============================================================

def _validate_gemini_result(
    result: dict[str, Any],
) -> dict[str, Any]:

    """
    Basic validation before saving Gemini output.
    """

    if not isinstance(
        result,
        dict,
    ):

        raise ValueError(
            "Gemini household result must be a JSON object."
        )


    guidance = result.get(
        "guidance"
    )


    if not isinstance(
        guidance,
        list,
    ):

        raise ValueError(
            "Gemini household result is missing guidance."
        )


    if len(
        guidance
    ) == 0:

        raise ValueError(
            "Gemini returned no household guidance."
        )


    valid_priorities = {
        "low",
        "medium",
        "high",
        "critical",
    }


    overall_priority = str(
        result.get(
            "overall_priority",
            "medium",
        )
    ).lower()


    if (
        overall_priority
        not in
        valid_priorities
    ):

        overall_priority = (
            "medium"
        )


    result[
        "overall_priority"
    ] = overall_priority


    result[
        "mode"
    ] = "gemini_grounded"


    if not result.get(
        "summary"
    ):

        result[
            "summary"
        ] = (
            "EcoLens prepared disposal guidance "
            "using the retrieved household knowledge."
        )


    if (
        "local_verification_required"
        not in
        result
    ):

        result[
            "local_verification_required"
        ] = True


    return result


# ============================================================
# SAVE GEMINI RESULT
# ============================================================

def _save_gemini_result(
    *,
    detection_session_id: int,
    response_language: str,
    gemini_result: dict[str, Any],
) -> int | None:

    """
    Replace the previously stored offline Household RAG
    response with the final Gemini-grounded response.

    The original RAG process already creates generated_advice.
    Therefore we update that same advice record instead of
    creating a duplicate.
    """

    connection = (
        _get_connection()
    )


    cursor = connection.cursor(
        dictionary=True
    )


    try:

        cursor.execute(
            """
            SELECT
                advice_id
            FROM generated_advice
            WHERE detection_session_id = %s
              AND audience_role = 'household'
            ORDER BY advice_id DESC
            LIMIT 1
            """,
            (
                detection_session_id,
            ),
        )


        row = cursor.fetchone()


        if row is None:

            connection.rollback()

            return None


        advice_id = int(
            row[
                "advice_id"
            ]
        )


        overall_priority = (
            str(
                gemini_result.get(
                    "overall_priority",
                    "medium",
                )
            )
            .lower()
        )


        if overall_priority not in {
            "low",
            "medium",
            "high",
            "critical",
        }:

            overall_priority = (
                "medium"
            )


        summary = str(
            gemini_result.get(
                "summary",
                "",
            )
        ).strip()


        response_json = json.dumps(
            _json_safe_value(
                gemini_result
            ),
            ensure_ascii=False,
        )


        local_verification_required = (
            1
            if gemini_result.get(
                "local_verification_required",
                True,
            )
            else 0
        )


        cursor.execute(
            """
            UPDATE generated_advice
            SET
                priority_level = %s,
                summary = %s,
                response_language = %s,
                response_json = %s,
                gemini_model = %s,
                prompt_version = %s,
                local_verification_required = %s
            WHERE advice_id = %s
            """,
            (
                overall_priority,
                summary,
                response_language,
                response_json,
                GEMINI_MODEL,
                HOUSEHOLD_GEMINI_PROMPT_VERSION,
                local_verification_required,
                advice_id,
            ),
        )


        connection.commit()


        return advice_id


    except Exception:

        connection.rollback()

        raise


    finally:

        cursor.close()

        connection.close()


def _build_initial_household_gemini_prompt(
    *,
    grounding_context: dict[str, Any],
) -> str:
    """
    Build the INITIAL Household Gemini prompt from:
    - YOLO detected classes,
    - verified Household RAG knowledge,
    - Household safety rules,
    - verified facilities.

    The existing Household RAG implementation remains unchanged.
    This helper only packages its retrieved context for Gemini.
    """

    detected_objects = (
        grounding_context.get(
            "detection",
            {}
        ).get(
            "detected_objects",
            []
        )
    )


    class_grounding = (
        grounding_context.get(
            "class_grounding",
            []
        )
    )


    knowledge: list[
        dict[str, Any]
    ] = []

    safety_rules: list[
        dict[str, Any]
    ] = []

    facilities: list[
        dict[str, Any]
    ] = []


    seen_knowledge_ids: set[
        int
    ] = set()

    seen_safety_rule_ids: set[
        int
    ] = set()

    seen_facility_ids: set[
        int
    ] = set()


    for class_context in (
        class_grounding
    ):

        for row in class_context.get(
            "verified_knowledge",
            []
        ):

            knowledge_id = row.get(
                "knowledge_id"
            )

            if knowledge_id is None:

                knowledge.append(
                    row
                )

                continue


            knowledge_id = int(
                knowledge_id
            )


            if (
                knowledge_id
                in
                seen_knowledge_ids
            ):

                continue


            seen_knowledge_ids.add(
                knowledge_id
            )

            knowledge.append(
                row
            )


        for row in class_context.get(
            "safety_rules",
            []
        ):

            rule_id = row.get(
                "safety_rule_id"
            )


            if rule_id is None:

                safety_rules.append(
                    row
                )

                continue


            rule_id = int(
                rule_id
            )


            if (
                rule_id
                in
                seen_safety_rule_ids
            ):

                continue


            seen_safety_rule_ids.add(
                rule_id
            )

            safety_rules.append(
                row
            )


        for row in class_context.get(
            "verified_facilities",
            []
        ):

            facility_id = row.get(
                "facility_id"
            )


            if facility_id is None:

                facilities.append(
                    row
                )

                continue


            facility_id = int(
                facility_id
            )


            if (
                facility_id
                in
                seen_facility_ids
            ):

                continue


            seen_facility_ids.add(
                facility_id
            )

            facilities.append(
                row
            )


    base_prompt = (
        build_household_prompt(
            detected_objects=(
                detected_objects
            ),
            knowledge=knowledge,
            safety_rules=(
                safety_rules
            ),
            facilities=facilities,
            initial_detection=True,
        )
    )


    return (
        base_prompt
        + """

============================================================
INITIAL ADVICE REQUIREMENTS
============================================================

This is the FIRST user-facing advice after YOLO detection.

For EACH detected waste class, use the supplied verified EcoLens
information to provide:

- a short overview of the detected item
- immediate actions
- segregation steps
- preparation steps
- temporary storage steps
- disposal or transfer steps
- safety precautions
- actions the household must not do
- realistic recycling or recovery opportunities
- 2 or 3 short benefits of proper disposal when supported
- 2 or 3 short harms or consequences of improper disposal
  when supported
- short environmental notes when supported

The detected class names and model_class_id values must match
the YOLO detection supplied above.

Do not create a facility, law, service, schedule, safety claim,
benefit, harm or environmental claim that is not supported by
the supplied EcoLens context.

If a requested field is not supported by verified context,
return an empty list for that field rather than inventing facts.

Return ONLY valid JSON matching the supplied response schema.
Do not add Markdown before or after the JSON.
"""
    )


# ============================================================
# GENERATE HOUSEHOLD ADVICE
# ============================================================

@household_bp.post(
    "/<int:user_id>/advice"
)
def generate_household_advice(
    user_id: int,
):

    """
    FINAL HOUSEHOLD PIPELINE

    YOLO
        ↓
    Detection session
        ↓
    Household RAG
        ↓
    Verified knowledge + safety information
        ↓
    Gemini
        ↓
    Detailed grounded disposal guidance
    """

    try:

        user_id = (
            _validate_positive_integer(
                user_id,
                "user_id",
            )
        )


        payload = request.get_json(
            silent=True
        )


        if payload is None:

            raise ValueError(
                "A JSON request body is required."
            )


        if not isinstance(
            payload,
            dict,
        ):

            raise ValueError(
                "The JSON request body must be an object."
            )


        detection_session_id = (
            _validate_positive_integer(

                payload.get(
                    "detection_session_id"
                ),

                "detection_session_id",
            )
        )


        language = payload.get(
            "language",
            "en",
        )


        if not isinstance(
            language,
            str,
        ):

            raise ValueError(
                "language must be a string."
            )


        language = (
            language
            .strip()
            .lower()
        )


        if language not in {
            "en",
            "bn",
        }:

            raise ValueError(
                "language must be 'en' or 'bn'."
            )


        # ====================================================
        # STEP 1
        # Run existing Household RAG.
        #
        # This performs retrieval first.
        # Gemini does NOT replace this stage.
        # ====================================================

        rag_result = (
            generate_household_advice_offline(

                user_id=user_id,

                detection_session_id=(
                    detection_session_id
                ),

                response_language="en",
            )
        )


        safe_rag_result = (
            _json_safe_value(
                rag_result
            )
        )


        # ====================================================
        # STEP 2
        # Rebuild the raw grounding bundle for the SAME
        # completed detection and the advice record created
        # by the existing Household RAG pipeline.
        #
        # The RAG itself is not changed.
        # ====================================================

        rag_advice_id = (
            _validate_positive_integer(
                rag_result.get(
                    "advice_id"
                ),
                "rag_result.advice_id",
            )
        )


        grounding_context = (
            build_household_chat_context(
                user_id=user_id,
                detection_session_id=(
                    detection_session_id
                ),
                advice_id=(
                    rag_advice_id
                ),
            )
        )


        # ====================================================
        # STEP 3
        # Build the INITIAL Gemini prompt from:
        #
        # YOLO classes + raw RAG knowledge + safety rules +
        # verified facilities.
        #
        # This uses the project's Household prompt with
        # initial_detection=True.
        # ====================================================

        gemini_prompt = (
            _build_initial_household_gemini_prompt(
                grounding_context=(
                    grounding_context
                ),
            )
        )


        # ====================================================
        # STEP 4
        # Send the grounded prompt to Gemini.
        # ====================================================

        try:

            gemini_result = (
                generate_grounded_json(
                    prompt=gemini_prompt,
                    json_schema=(
                        HOUSEHOLD_INITIAL_GEMINI_SCHEMA
                    ),
                    model=GEMINI_MODEL,
                )
            )


            gemini_result = (
                _validate_gemini_result(
                    gemini_result
                )
            )


            # ================================================
            # STEP 5
            # Store final Gemini-grounded answer.
            # ================================================

            advice_id = (
                _save_gemini_result(

                    detection_session_id=(
                        detection_session_id
                    ),

                    response_language=(
                        language
                    ),

                    gemini_result=(
                        gemini_result
                    ),
                )
            )


            # ================================================
            # STEP 6
            # Return detailed answer to React.
            # ================================================

            return jsonify(
                {

                    "success": True,

                    "message":
                        "Waste was detected, RAG knowledge "
                        "was retrieved and Gemini prepared "
                        "detailed disposal guidance.",

                    "advice_id":
                        advice_id,

                    "detection_session_id":
                        detection_session_id,

                    "mode":
                        "gemini_grounded",

                    "gemini_model":
                        GEMINI_MODEL,

                    "prompt_version":
                        HOUSEHOLD_GEMINI_PROMPT_VERSION,

                    **_json_safe_value(
                        gemini_result
                    ),
                }
            ), 201


        except Exception as gemini_error:

            # =================================================
            # IMPORTANT FALLBACK
            #
            # If Gemini temporarily fails, EcoLens still returns
            # the verified RAG guidance instead of completely
            # breaking household detection.
            # =================================================

            fallback = dict(
                safe_rag_result
            )


            fallback[
                "mode"
            ] = "offline_grounded_fallback"


            fallback[
                "gemini_error"
            ] = str(
                gemini_error
            )


            return jsonify(
                {

                    "success": True,

                    "message":
                        "RAG guidance was generated, but "
                        "Gemini could not be reached. "
                        "Offline grounded guidance is shown.",

                    **_json_safe_value(
                        fallback
                    ),
                }
            ), 201


    except ValueError as exc:

        return _error_response(
            str(exc),
            400,
        )


    except TypeError as exc:

        return _error_response(
            str(exc),
            400,
        )


    except Exception as exc:

        return _error_response(
            str(exc),
            500,
        )


# ============================================================
# HOUSEHOLD FOLLOW-UP CHAT
# ============================================================

@household_bp.post(
    "/<int:user_id>/chat"
)
def household_followup_chat(
    user_id: int,
):
    """
    Answer one follow-up question about an existing Household
    YOLO detection.

    This endpoint does not run YOLO again. It rebuilds the
    verified RAG context for the completed detection and sends
    that grounding, the saved initial advice, recent conversation
    messages and the new question to Gemini.
    """

    try:

        user_id = (
            _validate_positive_integer(
                user_id,
                "user_id",
            )
        )


        payload = request.get_json(
            silent=True
        )


        if payload is None:

            raise ValueError(
                "A JSON request body is required."
            )


        if not isinstance(
            payload,
            dict,
        ):

            raise ValueError(
                "The JSON request body must be an object."
            )


        detection_session_id = (
            _validate_positive_integer(
                payload.get(
                    "detection_session_id"
                ),
                "detection_session_id",
            )
        )


        advice_id = (
            _validate_positive_integer(
                payload.get(
                    "advice_id"
                ),
                "advice_id",
            )
        )


        message = payload.get(
            "message"
        )


        if not isinstance(
            message,
            str,
        ):

            raise ValueError(
                "message must be a string."
            )


        message = message.strip()


        if not message:

            raise ValueError(
                "message cannot be empty."
            )


        if len(message) > 1500:

            raise ValueError(
                "message cannot exceed 1500 characters."
            )


        language = payload.get(
            "language",
            "en",
        )


        if not isinstance(
            language,
            str,
        ):

            raise ValueError(
                "language must be a string."
            )


        language = (
            language
            .strip()
            .lower()
        )


        if language not in {
            "en",
            "bn",
        }:

            raise ValueError(
                "language must be 'en' or 'bn'."
            )


        history = payload.get(
            "history",
            [],
        )


        if history is None:

            history = []


        if not isinstance(
            history,
            list,
        ):

            raise ValueError(
                "history must be a list."
            )


        clean_history: list[
            dict[str, str]
        ] = []


        for item in history[-10:]:

            if not isinstance(
                item,
                dict,
            ):

                continue


            role = item.get(
                "role"
            )

            content = item.get(
                "content"
            )


            if role not in {
                "user",
                "assistant",
            }:

                continue


            if not isinstance(
                content,
                str,
            ):

                continue


            content = (
                content
                .strip()
            )


            if not content:

                continue


            clean_history.append(
                {
                    "role": role,
                    "content":
                        content[:2000],
                }
            )


        grounding_context = (
            build_household_chat_context(
                user_id=user_id,
                detection_session_id=(
                    detection_session_id
                ),
                advice_id=advice_id,
            )
        )


        chat_prompt = (
            build_household_chat_prompt(
                grounding_context=(
                    grounding_context
                ),
                user_message=message,
                conversation_history=(
                    clean_history
                ),
                response_language=(
                    language
                ),
            )
        )


        chat_schema = {
            "type": "object",

            "properties": {
                "answer": {
                    "type": "string",
                },

                "local_verification_required": {
                    "type": "boolean",
                },

                "grounding_note": {
                    "type": "string",
                },
            },

            "required": [
                "answer",
                "local_verification_required",
                "grounding_note",
            ],
        }


        try:

            gemini_result = (
                generate_grounded_json(
                    prompt=chat_prompt,
                    json_schema=(
                        chat_schema
                    ),
                    model=(
                        GEMINI_MODEL
                    ),
                )
            )


        except Exception as exc:

            return jsonify(
                {
                    "success": False,

                    "error":
                        "Gemini follow-up chat is "
                        "temporarily unavailable. "
                        "The initial grounded Household "
                        "guidance is still available.",

                    "gemini_error":
                        str(exc),
                }
            ), 503


        answer = gemini_result.get(
            "answer"
        )


        if (
            not isinstance(
                answer,
                str,
            )
            or not answer.strip()
        ):

            raise ValueError(
                "Gemini returned an empty chat answer."
            )


        grounding_note = (
            gemini_result.get(
                "grounding_note"
            )
        )


        if not isinstance(
            grounding_note,
            str,
        ):

            grounding_note = (
                "The response was generated "
                "from the current EcoLens "
                "detection and RAG context."
            )


        local_verification_required = (
            gemini_result.get(
                "local_verification_required",
                True,
            )
        )


        if not isinstance(
            local_verification_required,
            bool,
        ):

            local_verification_required = True


        return jsonify(
            {
                "success": True,

                "mode":
                    "gemini_grounded_chat",

                "gemini_model":
                    GEMINI_MODEL,

                "prompt_version":
                    HOUSEHOLD_CHAT_PROMPT_VERSION,

                "detection_session_id":
                    detection_session_id,

                "advice_id":
                    advice_id,

                "answer":
                    answer.strip(),

                "grounding_note":
                    grounding_note.strip(),

                "local_verification_required":
                    local_verification_required,
            }
        ), 200


    except ValueError as exc:

        return _error_response(
            str(exc),
            400,
        )


    except TypeError as exc:

        return _error_response(
            str(exc),
            400,
        )


    except Exception as exc:

        return _error_response(
            str(exc),
            500,
        )


# ============================================================
# GET HOUSEHOLD ADVICE HISTORY
# ============================================================

@household_bp.get(
    "/<int:user_id>/advice-history"
)
def get_advice_history(
    user_id: int,
):

    """
    Return previously generated Household advice.

    Example:

    GET /api/household/2/advice-history?limit=20
    """

    try:

        user_id = (
            _validate_positive_integer(
                user_id,
                "user_id",
            )
        )


        limit = (
            _parse_limit(
                request.args.get(
                    "limit"
                )
            )
        )


        rows = (
            get_household_advice_history(

                user_id=user_id,

                limit=limit,
            )
        )


        history: list[
            dict[str, Any]
        ] = []


        for row_value in rows:

            row = dict(
                row_value
            )


            stored_response = (
                row.pop(
                    "response_json",
                    None,
                )
            )


            row[
                "result"
            ] = (
                _parse_saved_json(
                    stored_response
                )
            )


            history.append(
                _json_safe_value(
                    row
                )
            )


        return jsonify(
            {

                "success":
                    True,

                "count":
                    len(
                        history
                    ),

                "history":
                    history,
            }
        ), 200


    except ValueError as exc:

        return _error_response(
            str(exc),
            400,
        )


    except Exception as exc:

        return _error_response(
            str(exc),
            500,
        )


# ============================================================
# GET ONE HOUSEHOLD ADVICE RECORD
# ============================================================

@household_bp.get(
    "/<int:user_id>/advice/<int:advice_id>"
)
def get_advice_by_id(
    user_id: int,
    advice_id: int,
):

    """
    Return one saved Household advice result.

    Example:

    GET /api/household/2/advice/1
    """

    try:

        user_id = (
            _validate_positive_integer(
                user_id,
                "user_id",
            )
        )


        advice_id = (
            _validate_positive_integer(
                advice_id,
                "advice_id",
            )
        )


        row = (
            get_household_advice_by_id(

                advice_id=advice_id,

                user_id=user_id,
            )
        )


        if row is None:

            return _error_response(
                (
                    "Household advice was not found, "
                    "or it does not belong to this user."
                ),
                404,
            )


        advice = dict(
            row
        )


        stored_response = (
            advice.pop(
                "response_json",
                None,
            )
        )


        advice[
            "result"
        ] = (
            _parse_saved_json(
                stored_response
            )
        )


        return jsonify(
            {

                "success":
                    True,

                "advice":
                    _json_safe_value(
                        advice
                    ),
            }
        ), 200


    except ValueError as exc:

        return _error_response(
            str(exc),
            400,
        )


    except Exception as exc:

        return _error_response(
            str(exc),
            500,
        )