from typing import Any, TypedDict


# ============================================================
# ALLOWED VALUES
# ============================================================

ALLOWED_ADVICE_MODES = {
    "offline_grounded",
    "gemini_grounded",
}

ALLOWED_DATA_QUALITY_STATUSES = {
    "complete",
    "partial",
    "insufficient",
}

ALLOWED_PRIORITIES = {
    "low",
    "medium",
    "high",
    "critical",
}


# ============================================================
# TYPE DEFINITIONS
# ============================================================

class AuthorityScope(TypedDict):
    authority_id: int
    authority_name: str
    organization_name: str | None

    region_id: int
    region_name: str
    region_type: str

    period_start: str
    period_end: str


class DataQualityResult(TypedDict):
    status: str
    completeness_percent: float
    limitations: list[str]


class AnalyticsSummaryItem(TypedDict):
    indicator: str
    value: float
    unit: str
    meaning: str


class AuthorityRecommendation(TypedDict):
    priority: str
    category: str
    title: str
    why: str

    actions: list[str]
    indicators_used: list[str]
    source_ids: list[int]

    human_review_required: bool


class AdviceSource(TypedDict):
    source_id: int
    title: str
    issuing_authority: str
    jurisdiction: str
    page_or_section: str
    last_checked_at: str | None
    source_url: str | None


class AuthorityAdviceResponse(TypedDict):
    mode: str

    scope: AuthorityScope
    data_quality: DataQualityResult

    analytics_summary: list[AnalyticsSummaryItem]
    recommendations: list[AuthorityRecommendation]
    source_list: list[AdviceSource]

    verified_facilities: list[dict[str, Any]]

    disclaimer: str


# ============================================================
# VALIDATION ERROR
# ============================================================

class AuthorityAdviceValidationError(ValueError):
    """Raised when an authority advice response is invalid."""


# ============================================================
# SMALL VALIDATION HELPERS
# ============================================================

def _require_dictionary(
    value: Any,
    field_name: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AuthorityAdviceValidationError(
            f"{field_name} must be a dictionary."
        )

    return value


def _require_list(
    value: Any,
    field_name: str,
) -> list[Any]:
    if not isinstance(value, list):
        raise AuthorityAdviceValidationError(
            f"{field_name} must be a list."
        )

    return value


def _require_string(
    value: Any,
    field_name: str,
    allow_empty: bool = False,
) -> str:
    if not isinstance(value, str):
        raise AuthorityAdviceValidationError(
            f"{field_name} must be a string."
        )

    if not allow_empty and not value.strip():
        raise AuthorityAdviceValidationError(
            f"{field_name} cannot be empty."
        )

    return value


def _require_integer(
    value: Any,
    field_name: str,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise AuthorityAdviceValidationError(
            f"{field_name} must be an integer."
        )

    return value


def _require_number(
    value: Any,
    field_name: str,
) -> float:
    if isinstance(value, bool):
        raise AuthorityAdviceValidationError(
            f"{field_name} must be numeric."
        )

    if not isinstance(value, (int, float)):
        raise AuthorityAdviceValidationError(
            f"{field_name} must be numeric."
        )

    return float(value)


def _validate_string_list(
    values: Any,
    field_name: str,
) -> list[str]:
    items = _require_list(
        values,
        field_name,
    )

    for index, item in enumerate(items):
        _require_string(
            item,
            f"{field_name}[{index}]",
        )

    return items


def _validate_integer_list(
    values: Any,
    field_name: str,
) -> list[int]:
    items = _require_list(
        values,
        field_name,
    )

    for index, item in enumerate(items):
        _require_integer(
            item,
            f"{field_name}[{index}]",
        )

    return items


# ============================================================
# SCOPE VALIDATION
# ============================================================

def _validate_scope(
    scope_value: Any,
) -> None:
    scope = _require_dictionary(
        scope_value,
        "scope",
    )

    required_fields = {
        "authority_id",
        "authority_name",
        "organization_name",
        "region_id",
        "region_name",
        "region_type",
        "period_start",
        "period_end",
    }

    missing_fields = required_fields - scope.keys()

    if missing_fields:
        raise AuthorityAdviceValidationError(
            "scope is missing: "
            + ", ".join(sorted(missing_fields))
        )

    authority_id = _require_integer(
        scope["authority_id"],
        "scope.authority_id",
    )

    if authority_id <= 0:
        raise AuthorityAdviceValidationError(
            "scope.authority_id must be greater than zero."
        )

    region_id = _require_integer(
        scope["region_id"],
        "scope.region_id",
    )

    if region_id <= 0:
        raise AuthorityAdviceValidationError(
            "scope.region_id must be greater than zero."
        )

    _require_string(
        scope["authority_name"],
        "scope.authority_name",
    )

    organization_name = scope["organization_name"]

    if organization_name is not None:
        _require_string(
            organization_name,
            "scope.organization_name",
        )

    _require_string(
        scope["region_name"],
        "scope.region_name",
    )

    _require_string(
        scope["region_type"],
        "scope.region_type",
    )

    _require_string(
        scope["period_start"],
        "scope.period_start",
    )

    _require_string(
        scope["period_end"],
        "scope.period_end",
    )


# ============================================================
# DATA-QUALITY VALIDATION
# ============================================================

def _validate_data_quality(
    data_quality_value: Any,
) -> None:
    data_quality = _require_dictionary(
        data_quality_value,
        "data_quality",
    )

    required_fields = {
        "status",
        "completeness_percent",
        "limitations",
    }

    missing_fields = (
        required_fields - data_quality.keys()
    )

    if missing_fields:
        raise AuthorityAdviceValidationError(
            "data_quality is missing: "
            + ", ".join(sorted(missing_fields))
        )

    status = _require_string(
        data_quality["status"],
        "data_quality.status",
    )

    if status not in ALLOWED_DATA_QUALITY_STATUSES:
        raise AuthorityAdviceValidationError(
            "data_quality.status must be complete, "
            "partial or insufficient."
        )

    completeness = _require_number(
        data_quality["completeness_percent"],
        "data_quality.completeness_percent",
    )

    if completeness < 0 or completeness > 100:
        raise AuthorityAdviceValidationError(
            "data_quality.completeness_percent "
            "must be between 0 and 100."
        )

    _validate_string_list(
        data_quality["limitations"],
        "data_quality.limitations",
    )


# ============================================================
# ANALYTICS-SUMMARY VALIDATION
# ============================================================

def _validate_analytics_summary(
    summary_value: Any,
) -> None:
    summary_items = _require_list(
        summary_value,
        "analytics_summary",
    )

    required_fields = {
        "indicator",
        "value",
        "unit",
        "meaning",
    }

    for index, item_value in enumerate(summary_items):
        item = _require_dictionary(
            item_value,
            f"analytics_summary[{index}]",
        )

        missing_fields = required_fields - item.keys()

        if missing_fields:
            raise AuthorityAdviceValidationError(
                f"analytics_summary[{index}] is missing: "
                + ", ".join(sorted(missing_fields))
            )

        _require_string(
            item["indicator"],
            f"analytics_summary[{index}].indicator",
        )

        _require_number(
            item["value"],
            f"analytics_summary[{index}].value",
        )

        _require_string(
            item["unit"],
            f"analytics_summary[{index}].unit",
        )

        _require_string(
            item["meaning"],
            f"analytics_summary[{index}].meaning",
        )


# ============================================================
# RECOMMENDATION VALIDATION
# ============================================================

def _validate_recommendations(
    recommendations_value: Any,
) -> None:
    recommendations = _require_list(
        recommendations_value,
        "recommendations",
    )

    required_fields = {
        "priority",
        "category",
        "title",
        "why",
        "actions",
        "indicators_used",
        "source_ids",
        "human_review_required",
    }

    for index, recommendation_value in enumerate(
        recommendations
    ):
        recommendation = _require_dictionary(
            recommendation_value,
            f"recommendations[{index}]",
        )

        missing_fields = (
            required_fields - recommendation.keys()
        )

        if missing_fields:
            raise AuthorityAdviceValidationError(
                f"recommendations[{index}] is missing: "
                + ", ".join(sorted(missing_fields))
            )

        priority = _require_string(
            recommendation["priority"],
            f"recommendations[{index}].priority",
        )

        if priority not in ALLOWED_PRIORITIES:
            raise AuthorityAdviceValidationError(
                f"recommendations[{index}].priority "
                "must be low, medium, high or critical."
            )

        _require_string(
            recommendation["category"],
            f"recommendations[{index}].category",
        )

        _require_string(
            recommendation["title"],
            f"recommendations[{index}].title",
        )

        _require_string(
            recommendation["why"],
            f"recommendations[{index}].why",
        )

        actions = _validate_string_list(
            recommendation["actions"],
            f"recommendations[{index}].actions",
        )

        if not actions:
            raise AuthorityAdviceValidationError(
                f"recommendations[{index}].actions "
                "must contain at least one action."
            )

        _validate_string_list(
            recommendation["indicators_used"],
            (
                f"recommendations[{index}]"
                ".indicators_used"
            ),
        )

        _validate_integer_list(
            recommendation["source_ids"],
            f"recommendations[{index}].source_ids",
        )

        if not isinstance(
            recommendation["human_review_required"],
            bool,
        ):
            raise AuthorityAdviceValidationError(
                f"recommendations[{index}]"
                ".human_review_required must be boolean."
            )


# ============================================================
# SOURCE VALIDATION
# ============================================================

def _validate_sources(
    sources_value: Any,
) -> None:
    sources = _require_list(
        sources_value,
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

    for index, source_value in enumerate(sources):
        source = _require_dictionary(
            source_value,
            f"source_list[{index}]",
        )

        missing_fields = required_fields - source.keys()

        if missing_fields:
            raise AuthorityAdviceValidationError(
                f"source_list[{index}] is missing: "
                + ", ".join(sorted(missing_fields))
            )

        source_id = _require_integer(
            source["source_id"],
            f"source_list[{index}].source_id",
        )

        if source_id <= 0:
            raise AuthorityAdviceValidationError(
                f"source_list[{index}].source_id "
                "must be greater than zero."
            )

        if source_id in seen_source_ids:
            raise AuthorityAdviceValidationError(
                f"Duplicate source_id found: {source_id}"
            )

        seen_source_ids.add(source_id)

        _require_string(
            source["title"],
            f"source_list[{index}].title",
        )

        _require_string(
            source["issuing_authority"],
            (
                f"source_list[{index}]"
                ".issuing_authority"
            ),
        )

        _require_string(
            source["jurisdiction"],
            f"source_list[{index}].jurisdiction",
        )

        _require_string(
            source["page_or_section"],
            (
                f"source_list[{index}]"
                ".page_or_section"
            ),
        )

        last_checked_at = source["last_checked_at"]

        if last_checked_at is not None:
            _require_string(
                last_checked_at,
                (
                    f"source_list[{index}]"
                    ".last_checked_at"
                ),
            )

        source_url = source["source_url"]

        if source_url is not None:
            _require_string(
                source_url,
                f"source_list[{index}].source_url",
            )


# ============================================================
# FACILITY VALIDATION
# ============================================================

def _validate_facilities(
    facilities_value: Any,
) -> None:
    facilities = _require_list(
        facilities_value,
        "verified_facilities",
    )

    for index, facility in enumerate(facilities):
        _require_dictionary(
            facility,
            f"verified_facilities[{index}]",
        )


# ============================================================
# COMPLETE RESPONSE VALIDATION
# ============================================================

def validate_authority_advice_response(
    response_value: Any,
) -> AuthorityAdviceResponse:
    """
    Validate the full authority RAG response.

    The same validator can be used for:
    - offline grounded output now;
    - Gemini structured output later.
    """

    response = _require_dictionary(
        response_value,
        "authority advice response",
    )

    required_fields = {
        "mode",
        "scope",
        "data_quality",
        "analytics_summary",
        "recommendations",
        "source_list",
        "verified_facilities",
        "disclaimer",
    }

    missing_fields = required_fields - response.keys()

    if missing_fields:
        raise AuthorityAdviceValidationError(
            "Authority advice response is missing: "
            + ", ".join(sorted(missing_fields))
        )

    mode = _require_string(
        response["mode"],
        "mode",
    )

    if mode not in ALLOWED_ADVICE_MODES:
        raise AuthorityAdviceValidationError(
            "mode must be offline_grounded "
            "or gemini_grounded."
        )

    _validate_scope(
        response["scope"]
    )

    _validate_data_quality(
        response["data_quality"]
    )

    _validate_analytics_summary(
        response["analytics_summary"]
    )

    _validate_recommendations(
        response["recommendations"]
    )

    _validate_sources(
        response["source_list"]
    )

    _validate_facilities(
        response["verified_facilities"]
    )

    _require_string(
        response["disclaimer"],
        "disclaimer",
    )

    return response  # type: ignore[return-value]