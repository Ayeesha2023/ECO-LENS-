from __future__ import annotations

from datetime import date
from typing import Any
from uuid import uuid4

from prompts.authority_chat_prompt import (
    build_authority_chat_prompt,
)
from prompts.authority_prompt import (
    build_authority_prompt,
)
from repositories.authority_repository import (
    complete_authority_advice_run,
    create_authority_advice_run,
    fail_authority_advice_run,
    get_active_authority_prompt_template,
    get_verified_facilities,
    save_analytics_snapshot,
    save_authority_knowledge_links,
    save_authority_rule_links,
)
from schemas.authority_advice_schema import (
    AuthorityAdviceResponse,
    validate_authority_advice_response,
)
from services.analytics_service import (
    build_authority_analytics,
)
from services.authority_rag_service import (
    _build_analytics_summary,
    _build_source_list,
    _json_safe_value,
)
from services.authority_retriever import (
    retrieve_verified_authority_knowledge,
)
from services.gemini_service import (
    DEFAULT_MODEL,
    generate_grounded_json,
)
from services.rule_engine import (
    evaluate_authority_rules,
)


AUTHORITY_GEMINI_SERVICE_VERSION = "authority-gemini-grounded-1.0"
AUTHORITY_CHAT_PROMPT_VERSION = "authority-gemini-chat-1.0"

VALID_PRIORITIES = {
    "low",
    "medium",
    "high",
    "critical",
}


def _normalise_language(
    response_language: str,
) -> str:
    language = str(response_language or "en").strip().lower()

    if language not in {"en", "bn"}:
        raise ValueError(
            "response_language must be 'en' or 'bn'."
        )

    return language


def _has_usable_analytics(
    analytics: dict[str, Any],
) -> bool:
    """Return True only when the selected period has operational signal."""

    reports = analytics.get("reports", {})
    assignments = analytics.get("assignments", {})
    waste = analytics.get("waste", {})

    return any(
        float(value or 0) > 0
        for value in (
            reports.get("submitted"),
            reports.get("completed"),
            reports.get("unresolved"),
            assignments.get("active"),
            assignments.get("completed"),
            waste.get("total_collected_kg"),
        )
    )


def _prompt_metadata(
    language: str,
) -> tuple[str | None, str]:
    template = get_active_authority_prompt_template(
        language_code=language,
    )

    if template is None:
        return None, AUTHORITY_GEMINI_SERVICE_VERSION

    system_prompt = template.get("system_prompt")
    template_name = str(
        template.get("template_name")
        or "community_authority_analytics_adviser"
    )
    template_version = str(
        template.get("template_version")
        or "unknown"
    )

    return (
        str(system_prompt) if system_prompt else None,
        f"{template_name}:{template_version}:{AUTHORITY_GEMINI_SERVICE_VERSION}",
    )


def _build_grounding_context(
    *,
    authority_id: int,
    start_date: date,
    end_date: date,
    response_language: str,
) -> dict[str, Any]:
    analytics = build_authority_analytics(
        authority_id=authority_id,
        start_date=start_date,
        end_date=end_date,
    )

    scope = analytics["scope"]

    triggered_rules = evaluate_authority_rules(
        analytics
    )

    knowledge_rows = retrieve_verified_authority_knowledge(
        region_id=scope["region_id"],
        triggered_rules=triggered_rules,
    )

    verified_facilities = _json_safe_value(
        get_verified_facilities(
            region_id=scope["region_id"]
        )
    )

    system_prompt, prompt_version = _prompt_metadata(
        response_language
    )

    return {
        "analytics": analytics,
        "scope": scope,
        "triggered_rules": triggered_rules,
        "knowledge_rows": knowledge_rows,
        "verified_facilities": verified_facilities,
        "system_prompt": system_prompt,
        "prompt_version": prompt_version,
        "has_usable_analytics": _has_usable_analytics(
            analytics
        ),
    }


def _safe_text(
    value: Any,
    fallback: str,
) -> str:
    text = str(value or "").strip()
    return text or fallback


def _normalise_recommendations(
    raw_recommendations: Any,
    *,
    allowed_source_ids: set[int],
    allowed_indicator_codes: set[str],
    has_usable_analytics: bool,
) -> list[dict[str, Any]]:
    """Restrict Gemini output to IDs and indicators already in RAG context."""

    if not has_usable_analytics:
        return []

    if not isinstance(raw_recommendations, list):
        return []

    result: list[dict[str, Any]] = []

    for item in raw_recommendations[:6]:
        if not isinstance(item, dict):
            continue

        raw_actions = item.get("actions")
        actions = [
            str(action).strip()
            for action in raw_actions
            if str(action).strip()
        ] if isinstance(raw_actions, list) else []

        if not actions:
            continue

        priority = str(
            item.get("priority", "medium")
        ).strip().lower()

        if priority not in VALID_PRIORITIES:
            priority = "medium"

        raw_source_ids = item.get("source_ids")
        source_ids: list[int] = []

        if isinstance(raw_source_ids, list):
            for value in raw_source_ids:
                try:
                    source_id = int(value)
                except (TypeError, ValueError):
                    continue

                if (
                    source_id in allowed_source_ids
                    and source_id not in source_ids
                ):
                    source_ids.append(source_id)

        raw_indicators = item.get("indicators_used")
        indicators_used = [
            str(code)
            for code in raw_indicators
            if str(code) in allowed_indicator_codes
        ] if isinstance(raw_indicators, list) else []

        result.append(
            {
                "priority": priority,
                "category": _safe_text(
                    item.get("category"),
                    "operations",
                ),
                "title": _safe_text(
                    item.get("title"),
                    "Grounded authority action",
                ),
                "why": _safe_text(
                    item.get("why"),
                    "This action is based on the supplied EcoLens context.",
                ),
                "actions": actions,
                "indicators_used": indicators_used,
                "source_ids": source_ids,
                "human_review_required": bool(
                    item.get("human_review_required", True)
                ),
            }
        )

    return result


def _build_analytics_fallback_recommendations(
    analytics: dict[str, Any],
    response_language: str,
) -> list[dict[str, Any]]:
    """Build a small analytics-only fallback if Gemini returns no actions.

    This is used only when usable verified analytics exist. It never names
    facilities, laws, vendors or costs.
    """

    waste = analytics.get("waste", {})
    category_rows = waste.get("category_breakdown", []) or []
    indicators = analytics.get("indicators", {})

    sorted_categories = sorted(
        [
            row
            for row in category_rows
            if float(row.get("weight_kg") or 0) > 0
        ],
        key=lambda row: float(row.get("weight_kg") or 0),
        reverse=True,
    )

    recommendations: list[dict[str, Any]] = []

    if sorted_categories:
        top = sorted_categories[0]
        name = str(
            top.get("category_name")
            or top.get("category_code")
            or "the leading waste category"
        )
        weight = round(float(top.get("weight_kg") or 0), 2)

        if response_language == "bn":
            recommendations.append(
                {
                    "priority": "medium",
                    "category": "waste planning",
                    "title": f"{name} ব্যবস্থাপনাকে অগ্রাধিকার দিন",
                    "why": (
                        f"যাচাইকৃত বর্জ্যের মধ্যে {name} সর্বাধিক, মোট {weight} কেজি। "
                        "এই বর্জ্যধারার জন্য সংগ্রহ, আলাদা রাখা ও পুনরুদ্ধার সক্ষমতা পর্যালোচনা করা যুক্তিযুক্ত।"
                    ),
                    "actions": [
                        f"{name}-এর জন্য আলাদা সংগ্রহ ও অস্থায়ী সংরক্ষণ সক্ষমতা মূল্যায়ন করুন।",
                        "পরবর্তী কয়েকটি যাচাইকৃত পরিচ্ছন্নতার রেকর্ডে একই প্রবণতা থাকে কি না তা পর্যবেক্ষণ করুন।",
                    ],
                    "indicators_used": [],
                    "source_ids": [],
                    "human_review_required": True,
                }
            )
        else:
            recommendations.append(
                {
                    "priority": "medium",
                    "category": "waste planning",
                    "title": f"Prioritize {name} management",
                    "why": (
                        f"{name} is the largest verified waste category at {weight} kg. "
                        "It is reasonable to review collection, segregation, storage and recovery capacity for this waste stream."
                    ),
                    "actions": [
                        f"Evaluate dedicated collection and temporary-storage capacity for {name}.",
                        "Track the next verified cleanup records to confirm whether this category remains dominant before making a larger investment.",
                    ],
                    "indicators_used": [],
                    "source_ids": [],
                    "human_review_required": True,
                }
            )

    recycling_share = float(
        indicators.get("recycling_share_percent") or 0
    )
    recyclable_weight = sum(
        float(row.get("weight_kg") or 0)
        for row in sorted_categories
        if "recycl" in str(
            row.get("category_name") or ""
        ).lower()
    )

    if recyclable_weight > 0 and recycling_share <= 0:
        if response_language == "bn":
            recommendations.append(
                {
                    "priority": "high",
                    "category": "recycling",
                    "title": "পুনর্ব্যবহারযোগ্য বর্জ্যের প্রবাহ পর্যালোচনা করুন",
                    "why": (
                        f"যাচাইকৃত ডেটায় {round(recyclable_weight, 2)} কেজি পুনর্ব্যবহারযোগ্য শ্রেণির বর্জ্য আছে, "
                        "কিন্তু রেকর্ড করা recycling share 0%।"
                    ),
                    "actions": [
                        "পুনর্ব্যবহারযোগ্য বর্জ্য আলাদা করা, সংরক্ষণ ও হস্তান্তরের বর্তমান প্রক্রিয়া যাচাই করুন।",
                        "উপযুক্ত পুনরুদ্ধার/রিসাইক্লিং ব্যবস্থার জন্য একটি ছোট পরিসরের সংগ্রহ বা sorting point মূল্যায়ন করুন।",
                    ],
                    "indicators_used": ["recycling_share_percent"],
                    "source_ids": [],
                    "human_review_required": True,
                }
            )
        else:
            recommendations.append(
                {
                    "priority": "high",
                    "category": "recycling",
                    "title": "Review the recyclable-waste pathway",
                    "why": (
                        f"The verified waste mix contains {round(recyclable_weight, 2)} kg of recyclable-category material, "
                        "while the recorded recycling share is 0%."
                    ),
                    "actions": [
                        "Check whether recyclable material is being segregated, stored and handed off consistently after collection.",
                        "Evaluate a small sorting/material-recovery collection point or covered recyclable-storage area before committing to larger infrastructure.",
                    ],
                    "indicators_used": ["recycling_share_percent"],
                    "source_ids": [],
                    "human_review_required": True,
                }
            )

    return recommendations[:4]


def _build_gemini_response(
    *,
    raw_result: dict[str, Any],
    context: dict[str, Any],
    response_language: str,
) -> AuthorityAdviceResponse:
    analytics = context["analytics"]
    scope = context["scope"]
    knowledge_rows = context["knowledge_rows"]
    facilities = context["verified_facilities"]
    has_usable = context["has_usable_analytics"]

    source_list = _build_source_list(
        knowledge_rows
    )

    allowed_source_ids = {
        int(item["source_id"])
        for item in source_list
        if item.get("source_id") is not None
    }

    allowed_indicator_codes = set(
        analytics.get("indicators", {}).keys()
    )

    recommendations = _normalise_recommendations(
        raw_result.get("recommendations"),
        allowed_source_ids=allowed_source_ids,
        allowed_indicator_codes=allowed_indicator_codes,
        has_usable_analytics=has_usable,
    )

    if has_usable and not recommendations:
        recommendations = _build_analytics_fallback_recommendations(
            analytics,
            response_language,
        )

    limitations: list[str] = []

    if not has_usable:
        limitations.append(
            "No usable operational analytics were available for the selected period."
        )

    if not knowledge_rows:
        limitations.append(
            "No verified Community Authority knowledge records matched the selected analytics context."
        )

    if not facilities:
        limitations.append(
            "No verified disposal or recovery facility was available for this region."
        )

    if response_language == "bn":
        summary = _safe_text(
            raw_result.get("summary"),
            (
                "নির্বাচিত সময়সীমার যাচাইকৃত EcoLens তথ্যের ভিত্তিতে "
                "কর্তৃপক্ষের জন্য পরামর্শ প্রস্তুত করা হয়েছে।"
                if has_usable
                else (
                    "নির্বাচিত সময়সীমায় পর্যাপ্ত ব্যবহারযোগ্য অপারেশনাল "
                    "অ্যানালিটিক্স নেই। আরও যাচাইকৃত তথ্য প্রয়োজন।"
                )
            ),
        )
        disclaimer = _safe_text(
            raw_result.get("disclaimer"),
            "এটি সিদ্ধান্ত-সহায়ক তথ্য; গুরুত্বপূর্ণ পদক্ষেপের আগে মানব যাচাই প্রয়োজন।",
        )
    else:
        summary = _safe_text(
            raw_result.get("summary"),
            (
                "EcoLens prepared grounded authority guidance from the verified analytics and RAG context."
                if has_usable
                else (
                    "There is not enough usable operational analytics in the selected period to generate grounded recommendations."
                )
            ),
        )
        disclaimer = _safe_text(
            raw_result.get("disclaimer"),
            "This is decision-support information and requires human review before operational action.",
        )

    response: dict[str, Any] = {
        "mode": "gemini_grounded",
        "scope": {
            "authority_id": int(scope["authority_id"]),
            "authority_name": str(scope["authority_name"]),
            "organization_name": scope.get("organization_name"),
            "region_id": int(scope["region_id"]),
            "region_name": str(scope["region_name"]),
            "region_type": str(scope["region_type"]),
            "period_start": str(scope["period_start"]),
            "period_end": str(scope["period_end"]),
        },
        "data_quality": {
            "status": analytics["data_quality"]["status"],
            "completeness_percent": float(
                analytics["data_quality"]["completeness_percent"]
            ),
            "limitations": limitations,
        },
        "analytics_summary": _build_analytics_summary(
            analytics
        ),
        "recommendations": recommendations,
        "source_list": source_list,
        "verified_facilities": facilities,
        "disclaimer": disclaimer,
        "summary": summary,
        "response_language": response_language,
    }

    return validate_authority_advice_response(
        response
    )


def generate_authority_gemini_advice(
    *,
    authority_id: int,
    start_date: date,
    end_date: date,
    response_language: str = "en",
) -> dict[str, Any]:
    """Generate a grounded Authority recommendation using RAG + Gemini."""

    if authority_id <= 0:
        raise ValueError(
            "authority_id must be greater than zero."
        )

    language = _normalise_language(
        response_language
    )

    context = _build_grounding_context(
        authority_id=authority_id,
        start_date=start_date,
        end_date=end_date,
        response_language=language,
    )

    prompt = build_authority_prompt(
        authority=context["scope"],
        analytics=context["analytics"],
        triggered_rules=context["triggered_rules"],
        knowledge=context["knowledge_rows"],
        facilities=context["verified_facilities"],
        response_language=language,
        system_prompt=context["system_prompt"],
        has_usable_analytics=context["has_usable_analytics"],
    )

    advice_run_id: int | None = None

    try:
        snapshot_id = save_analytics_snapshot(
            analytics=context["analytics"],
            period_type="custom",
        )

        advice_run_id = create_authority_advice_run(
            authority_id=authority_id,
            region_id=context["scope"]["region_id"],
            snapshot_id=snapshot_id,
            request_uuid=str(uuid4()),
            requested_by_user_id=context["scope"]["authority_user_id"],
            response_language=language,
            gemini_model=DEFAULT_MODEL,
            prompt_version=context["prompt_version"],
        )

        raw_result = generate_grounded_json(
            prompt=prompt,
            model=DEFAULT_MODEL,
        )

        result = _build_gemini_response(
            raw_result=raw_result,
            context=context,
            response_language=language,
        )

        save_authority_rule_links(
            advice_run_id=advice_run_id,
            triggered_rules=context["triggered_rules"],
        )

        save_authority_knowledge_links(
            advice_run_id=advice_run_id,
            knowledge_rows=context["knowledge_rows"],
            exact_region_id=context["scope"]["region_id"],
        )

        complete_authority_advice_run(
            advice_run_id=advice_run_id,
            executive_summary=str(
                result.get("summary")
                or "Grounded Authority Gemini guidance generated."
            ),
            advice_response=result,
            limitations=result["data_quality"]["limitations"],
        )

        return {
            "advice_run_id": advice_run_id,
            "snapshot_id": snapshot_id,
            "response_language": language,
            "gemini_model": DEFAULT_MODEL,
            "prompt_version": context["prompt_version"],
            "result": result,
        }

    except Exception as exc:
        if advice_run_id is not None:
            fail_authority_advice_run(
                advice_run_id=advice_run_id,
                error_message=str(exc),
            )
        raise


def generate_authority_chat_reply(
    *,
    authority_id: int,
    start_date: date,
    end_date: date,
    user_message: str,
    response_language: str = "en",
    conversation_history: list[dict[str, Any]] | None = None,
    initial_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Answer a follow-up Authority question using the same grounded context."""

    if authority_id <= 0:
        raise ValueError(
            "authority_id must be greater than zero."
        )

    message = str(user_message or "").strip()

    if not message:
        raise ValueError(
            "message cannot be empty."
        )

    if len(message) > 2000:
        raise ValueError(
            "message is too long."
        )

    language = _normalise_language(
        response_language
    )

    history = conversation_history or []

    if not isinstance(history, list):
        raise ValueError(
            "conversation_history must be a list."
        )

    safe_history: list[dict[str, str]] = []

    for item in history[-20:]:
        if not isinstance(item, dict):
            continue

        role = str(item.get("role", "")).strip().lower()
        content = str(item.get("content", "")).strip()

        if role not in {"user", "assistant"} or not content:
            continue

        safe_history.append(
            {
                "role": role,
                "content": content[:3000],
            }
        )

    context = _build_grounding_context(
        authority_id=authority_id,
        start_date=start_date,
        end_date=end_date,
        response_language=language,
    )

    prompt = build_authority_chat_prompt(
        system_prompt=context["system_prompt"],
        authority=context["scope"],
        analytics=context["analytics"],
        triggered_rules=context["triggered_rules"],
        knowledge=context["knowledge_rows"],
        facilities=context["verified_facilities"],
        initial_result=initial_result,
        conversation_history=safe_history,
        user_message=message,
        response_language=language,
        has_usable_analytics=context["has_usable_analytics"],
    )

    raw_result = generate_grounded_json(
        prompt=prompt,
        model=DEFAULT_MODEL,
    )

    if not isinstance(raw_result, dict):
        raise RuntimeError(
            "Gemini Authority chat returned an invalid response."
        )

    answer = str(raw_result.get("answer") or "").strip()

    if not answer:
        raise RuntimeError(
            "Gemini Authority chat returned an empty answer."
        )

    allowed_source_ids = {
        int(row["source_id"])
        for row in context["knowledge_rows"]
        if row.get("source_id") is not None
    }

    sources_used: list[int] = []
    raw_sources = raw_result.get("sources_used")

    if isinstance(raw_sources, list):
        for value in raw_sources:
            try:
                source_id = int(value)
            except (TypeError, ValueError):
                continue

            if (
                source_id in allowed_source_ids
                and source_id not in sources_used
            ):
                sources_used.append(source_id)

    grounding_notes = raw_result.get("grounding_notes")

    if not isinstance(grounding_notes, list):
        grounding_notes = []

    grounding_notes = [
        str(note).strip()
        for note in grounding_notes
        if str(note).strip()
    ][:5]

    return {
        "response_language": language,
        "gemini_model": DEFAULT_MODEL,
        "prompt_version": AUTHORITY_CHAT_PROMPT_VERSION,
        "result": {
            "answer": answer,
            "sources_used": sources_used,
            "grounding_notes": grounding_notes,
            "insufficient_information": bool(
                raw_result.get("insufficient_information", False)
            ),
        },
    }