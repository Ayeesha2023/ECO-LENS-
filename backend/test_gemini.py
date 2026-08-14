from services.gemini_service import (
    generate_grounded_json,
)


def main():
    schema = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
            },
            "message": {
                "type": "string",
            },
        },
        "required": [
            "status",
            "message",
        ],
    }

    response = generate_grounded_json(
        prompt="""
Return a JSON response.

status must be "success".

message must say that the ECO-LENS
Gemini connection is working.
""",
        json_schema=schema,
    )

    print(response)


if __name__ == "__main__":
    main()