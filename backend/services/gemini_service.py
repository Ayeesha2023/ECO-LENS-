import json
import os
from typing import Any

from dotenv import load_dotenv
from google import genai


load_dotenv()


DEFAULT_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.6-flash",
)


def _get_api_key() -> str:
    """Return the configured Gemini API key."""

    api_key = os.getenv(
        "GEMINI_API_KEY",
        "",
    ).strip()

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing from .env."
        )

    return api_key


def generate_grounded_json(
    prompt: str,
    json_schema: dict[str, Any] | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """
    Send a grounded ECO-LENS prompt to Gemini.

    Gemini is expected to use the RAG context provided
    inside the prompt rather than inventing missing facts.
    """

    if not isinstance(prompt, str):
        raise TypeError(
            "prompt must be a string."
        )

    prompt = prompt.strip()

    if not prompt:
        raise ValueError(
            "prompt cannot be empty."
        )

    client = genai.Client(
        api_key=_get_api_key()
    )

    model_name = (
        model
        or DEFAULT_MODEL
    )

    response_format: dict[str, Any] = {
        "type": "text",
        "mime_type": "application/json",
    }

    if json_schema is not None:
        response_format["schema"] = (
            json_schema
        )

    interaction = client.interactions.create(
        model=model_name,
        input=prompt,
        response_format=response_format,
    )

    raw_text = interaction.output_text

    if not raw_text:
        raise RuntimeError(
            "Gemini returned an empty response."
        )

    try:
        parsed = json.loads(raw_text)

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Gemini did not return valid JSON."
        ) from exc

    if not isinstance(parsed, dict):
        raise RuntimeError(
            "Gemini response must be "
            "a JSON object."
        )

    return parsed