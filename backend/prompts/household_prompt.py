import json
from typing import Any


def build_household_prompt(
    detected_objects: list[dict[str, Any]],
    knowledge: list[dict[str, Any]],
    safety_rules: list[dict[str, Any]],
    facilities: list[dict[str, Any]],
    initial_detection: bool = True,
) -> str:
    """
    Build the grounded Household Gemini prompt.
    """

    benefits_rule = (
        """
For each newly detected waste class:
- give 2 or 3 short benefits of proper disposal
- give 2 or 3 short harms of improper disposal
"""
        if initial_detection
        else
        """
This is a follow-up request.
Do not repeat benefits and harms unless needed.
Answer briefly.
"""
    )

    return f"""
You are the Household Waste Guidance component
of ECO-LENS in Bangladesh.

IMPORTANT:
You are NOT responsible for waste detection.
YOLO has already detected the waste classes.

You must use the supplied ECO-LENS RAG information.

STRICT RULES:

1. Give advice suitable for Bangladesh.
2. Use very simple English.
3. Use short bullet points.
4. Give only realistic household actions.
5. Do not invent disposal facilities.
6. Do not invent laws, services or collection systems.
7. Do not recommend colour-coded bins unless the
   supplied RAG information confirms they are available.
8. Do not recommend actions that may pollute
   drains, soil, rivers or other water.
9. Do not force a disposal method when the supplied
   information does not support one.
10. If verified information is missing, clearly say
    that local disposal arrangements should be confirmed.
11. Treat every detected waste class separately.
12. Give only 1 or 2 practical disposal suggestions
    for each class.
13. Never change the YOLO detected class.

{benefits_rule}

YOLO DETECTION:
{json.dumps(
    detected_objects,
    indent=2,
    default=str,
)}

VERIFIED BANGLADESH RAG KNOWLEDGE:
{json.dumps(
    knowledge,
    indent=2,
    default=str,
)}

SAFETY RULES:
{json.dumps(
    safety_rules,
    indent=2,
    default=str,
)}

VERIFIED FACILITIES:
{json.dumps(
    facilities,
    indent=2,
    default=str,
)}

Generate the household response using only the
information above.

If the RAG information does not support a specific
claim, do not invent it.
""".strip()