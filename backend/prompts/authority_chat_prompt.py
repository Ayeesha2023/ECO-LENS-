import json
from typing import Any

from prompts.authority_prompt import (
    DEFAULT_AUTHORITY_SYSTEM_PROMPT,
)


def _language_instruction(
    response_language: str,
) -> str:
    if response_language == "bn":
        return (
            "Answer the authority in clear natural Bangla. Keep source "
            "IDs and machine-readable keys in English."
        )

    return "Answer the authority in clear, simple English."


def build_authority_chat_prompt(
    *,
    system_prompt: str | None,
    authority: dict[str, Any],
    analytics: dict[str, Any],
    triggered_rules: list[dict[str, Any]],
    knowledge: list[dict[str, Any]],
    facilities: list[dict[str, Any]],
    initial_result: dict[str, Any] | None,
    conversation_history: list[dict[str, Any]],
    user_message: str,
    response_language: str,
    has_usable_analytics: bool,
) -> str:
    """Build the grounded follow-up prompt for Authority planning chat."""

    active_system_prompt = (
        str(system_prompt).strip()
        if system_prompt and str(system_prompt).strip()
        else DEFAULT_AUTHORITY_SYSTEM_PROMPT
    )

    analytics_rule = (
        (
            "Usable operational analytics are available. Give a useful "
            "answer based on those analytics even if no matched RAG source "
            "or verified facility record is available."
        )
        if has_usable_analytics
        else (
            "Operational analytics are effectively empty for this period. "
            "Do not invent trends or recommendations; explain what data is "
            "needed."
        )
    )

    return f"""
{active_system_prompt}

You are answering a follow-up planning question from the same Community
Authority.

LANGUAGE:
{_language_instruction(response_language)}

HOW TO USE THE CONTEXT:
1. Answer the user's actual question directly and lead with the practical recommendation, not with limitations.
2. ECO-LENS analytics are valid factual grounding for operational and
   planning advice.
3. You may infer sensible planning priorities from the verified waste mix,
   report load, assignment performance and handling outcomes.
4. You may recommend general facility TYPES or operational capabilities
   when the analytics support them. For example, if recyclable plastic and
   paper dominate, you may suggest evaluating sorting/material-recovery and
   covered storage capacity. If e-waste is present, you may suggest a
   dedicated e-waste collection/temporary-storage point.
5. Such suggestions must be clearly framed as options to evaluate or
   prioritize, not claims that a facility already exists or that a specific
   law requires it.
6. Verified RAG knowledge is needed for Bangladesh-specific legal,
   regulatory, policy or officially sourced factual claims.
7. Verified facility records are needed only to name or describe an actual
   facility in this locality.
8. Never invent named facilities, laws, vendors, costs, schedules or local
   procedures.
9. Do not say the information is insufficient merely because RAG knowledge
   or facility records are absent when usable analytics can still answer
   the planning question.
10. If only part of the question can be answered, answer the supported part
    first and place any caveat at the end.
11. Do not repeatedly say that human review is required. Mention human
    review only when the user is asking about a specific capital investment,
    legal/regulatory action, named facility, or other decision where that
    caution materially matters.
12. Do not treat missing RAG documents as a reason to weaken ordinary
    analytics-based operational advice.
13. {analytics_rule}
14. The previous AI result is conversational context, not an independent
    factual source. If it conflicts with current analytics, follow current
    analytics.
15. Use source IDs only when they occur in verified knowledge below.

Return ONLY JSON:
{{
  "answer": "direct, practical user-facing answer",
  "sources_used": [1, 2],
  "grounding_notes": ["short note"],
  "insufficient_information": false
}}

AUTHORITY:
{json.dumps(authority, indent=2, default=str, ensure_ascii=False)}

COMMUNITY ANALYTICS:
{json.dumps(analytics, indent=2, default=str, ensure_ascii=False)}

TRIGGERED RULES:
{json.dumps(triggered_rules, indent=2, default=str, ensure_ascii=False)}

VERIFIED RAG KNOWLEDGE:
{json.dumps(knowledge, indent=2, default=str, ensure_ascii=False)}

VERIFIED FACILITIES:
{json.dumps(facilities, indent=2, default=str, ensure_ascii=False)}

INITIAL GEMINI RESULT:
{json.dumps(initial_result or {}, indent=2, default=str, ensure_ascii=False)}

CONVERSATION HISTORY:
{json.dumps(conversation_history, indent=2, default=str, ensure_ascii=False)}

USER MESSAGE:
{user_message}
""".strip()