from google import genai

from config import Config


def test_gemini_connection() -> str:
    """Send a harmless connection test to Gemini."""

    if not Config.GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY is missing from backend/.env"
        )

    client = genai.Client(
        api_key=Config.GEMINI_API_KEY
    )

    response = client.models.generate_content(
        model=Config.GEMINI_MODEL,
        contents=(
            "Reply with exactly: "
            "ECO-LENS Gemini connection successful"
        ),
    )

    if not response.text:
        raise RuntimeError(
            "Gemini returned an empty response."
        )

    return response.text.strip()