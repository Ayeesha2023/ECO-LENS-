from services.gemini_service import (
    test_gemini_connection,
)


def main() -> None:
    result = test_gemini_connection()
    print(result)


if __name__ == "__main__":
    main()