import json
from typing import Any


DEFAULT_AUTHORITY_SYSTEM_PROMPT = """
You are the Municipal/Community Authority decision-support component
of ECO-LENS Bangladesh.

Use ECO-LENS analytics as factual evidence about this authority's actual
operations. Verified RAG knowledge and verified facilities strengthen
local or regulatory claims, but they are not required for you to give
reasonable planning advice when usable analytics already exist.

You MAY provide practical planning options, operational priorities and
facility TYPES that logically follow from the supplied analytics. Phrase
these as recommendations to consider or evaluate, not as claims that a
specific local facility, law, service, cost or procedure already exists.

Never invent named facilities, laws, statutory requirements, local
services, exact costs, percentages, trends or procedures that are not in
the supplied context.

Only when the supplied operational analytics are effectively empty should
you say that more verified data is required instead of generating advice.
""".strip()


def _language_instruction(
    response_language: str,
) -> str:
    if response_language == "bn":
        return (
            "Write every user-facing recommendation, explanation, "
            "summary, action and disclaimer in clear natural Bangla. "
            "Keep JSON property names, IDs, indicator codes and other "
            "machine-readable keys in English."
        )

    return (
        "Write every user-facing recommendation, explanation, summary, "
        "action and disclaimer in clear, simple English."
    )


def build_authority_prompt(
    authority: dict[str, Any],
    analytics: dict[str, Any],
    triggered_rules: list[dict[str, Any]],
    knowledge: list[dict[str, Any]],
    facilities: list[dict[str, Any]],
    response_language: str = "en",
    system_prompt: str | None = None,
    has_usable_analytics: bool = True,
) -> str:
    """Build the Authority RAG + Gemini planning prompt."""

    response_language = str(response_language).strip().lower()

    if response_language not in {"en", "bn"}:
        raise ValueError(
            "response_language must be 'en' or 'bn'."
        )

    active_system_prompt = (
        str(system_prompt).strip()
        if system_prompt and str(system_prompt).strip()
        else DEFAULT_AUTHORITY_SYSTEM_PROMPT
    )

    analytics_rule = (
        (
            "USABLE OPERATIONAL ANALYTICS ARE AVAILABLE. You MUST use "
            "them to provide useful, actionable decision-support advice. "
            "The absence of matched RAG knowledge or verified facility "
            "records is a limitation on local factual claims, NOT a reason "
            "to return no recommendations."
        )
        if has_usable_analytics
        else (
            "NO USABLE OPERATIONAL ANALYTICS ARE AVAILABLE FOR THIS "
            "PERIOD. Do not invent trends, percentages, infrastructure "
            "needs or operational recommendations. Return an empty "
            "recommendations array and explain that more verified "
            "operational data is required."
        )
    )

    return f"""
{active_system_prompt}

IMPORTANT INTERPRETATION FOR ECO-LENS:
- Verified analytics themselves are valid grounding for data-driven
  planning recommendations.
- RAG knowledge is required only when you make a Bangladesh-specific,
  legal, regulatory, policy or officially sourced factual claim.
- Verified facility records are required only when you name or describe
  an actual facility that exists in the authority's context.
- You MAY recommend general facility TYPES or capacity priorities based
  on the waste mix. Examples include a sorting area, covered recyclable
  storage, a material-recovery point, composting capacity, or a dedicated
  e-waste collection/storage point, when the supplied waste mix supports
  that suggestion.
- When recommending a facility type, phrase it as "consider", "evaluate",
  "prioritize" or "assess the need for". Do not claim that such a facility
  already exists or that a law requires it unless verified context says so.

LANGUAGE RULE:
{_language_instruction(response_language)}

GROUNDING RULES:
1. Use the supplied community analytics exactly as provided.
2. Do not change numeric values.
3. Connect recommendations to actual supplied analytics, waste categories,
   indicators or triggered rules.
4. If recyclable material is present but recorded recycling is low or zero,
   you may recommend reviewing segregation, collection, temporary storage,
   recovery partnerships or tracking practices as planning options.
5. If e-waste or hazardous categories are present, you may recommend
   evaluating dedicated safe collection/temporary-storage arrangements,
   without inventing a named facility or legal requirement.
6. If one waste category dominates the verified waste mix, you may
   prioritize infrastructure or operational capacity for that category.
7. Use verified RAG knowledge when available to make the advice more
   specific and cite only source IDs that actually appear below.
8. Use verified facility records when available. Never invent a facility.
9. Never invent named laws, regulations, costs, vendors, collection
   schedules or local procedures.
10. Lack of verified RAG knowledge or facility records does NOT by itself
    make the analytics insufficient.
11. {analytics_rule}

Return ONLY a JSON object with this shape:
{{
  "summary": "short user-facing overview",
  "recommendations": [
    {{
      "priority": "low|medium|high|critical",
      "category": "short category",
      "title": "short title",
      "why": "grounded explanation using the supplied analytics",
      "actions": ["action 1", "action 2"],
      "indicators_used": ["existing_indicator_code"],
      "source_ids": [1, 2],
      "human_review_required": true
    }}
  ],
  "disclaimer": "short grounded decision-support disclaimer"
}}

AUTHORITY:
{json.dumps(authority, indent=2, default=str, ensure_ascii=False)}

COMMUNITY ANALYTICS:
{json.dumps(analytics, indent=2, default=str, ensure_ascii=False)}

TRIGGERED ECO-LENS RULES:
{json.dumps(triggered_rules, indent=2, default=str, ensure_ascii=False)}

VERIFIED BANGLADESH AUTHORITY KNOWLEDGE:
{json.dumps(knowledge, indent=2, default=str, ensure_ascii=False)}

VERIFIED FACILITIES / INFRASTRUCTURE:
{json.dumps(facilities, indent=2, default=str, ensure_ascii=False)}

VERIFIED SOURCES:
{json.dumps(
    [
        {{
            "source_id": row.get("source_id"),
            "title": row.get("source_title"),
            "issuing_authority": row.get("issuing_authority"),
        }}
        for row in knowledge
        if row.get("source_id") is not None
    ],
    indent=2,
    default=str,
    ensure_ascii=False,
)}
""".strip()