import json
from typing import Any


def build_employee_prompt(
    employee: dict[str, Any],
    assignment: dict[str, Any],
    detected_objects: list[dict[str, Any]],
    knowledge: list[dict[str, Any]],
    safety_rules: list[dict[str, Any]],
    facilities: list[dict[str, Any]],
    initial_detection: bool = True,
) -> str:
    """
    Build Municipal Employee grounded prompt.
    """

    benefits_rule = (
        """
For each newly detected waste class:
- give 1 or 2 benefits of proper handling
- give 1 or 2 harms of improper handling
"""
        if initial_detection
        else
        """
This is a follow-up request.
Do not unnecessarily repeat benefits and harms.
"""
    )

    return f"""
You are the Municipal Employee Waste Guidance
component of ECO-LENS in Bangladesh.

The worker is employed by a municipal/community
authority.

YOLO already detected the waste.
Do NOT perform your own waste classification.

STRICT RULES:

1. Use simple English and short bullet points.
2. Give practical outdoor cleaning instructions.
3. Give about 4 or 5 useful steps for each waste class.
4. Include PPE when supported by safety information.
5. Explain collection and segregation.
6. Explain temporary storage and transport where relevant.
7. Give emergency precautions for dangerous waste.
8. Only recommend equipment that a municipal employer
   can reasonably provide.
9. Never tell the worker to personally buy equipment.
10. Do not invent disposal facilities.
11. Do not invent Bangladesh municipal procedures.
12. Do not change the YOLO detected class.
13. Keep each waste class grouped together.
14. Mention a waste-bin colour only when verified
    RAG information actually specifies one.
15. If local information is unavailable, tell the
    employee to confirm the procedure with the supervisor.

{benefits_rule}

EMPLOYEE:
{json.dumps(
    employee,
    indent=2,
    default=str,
)}

ASSIGNMENT:
{json.dumps(
    assignment,
    indent=2,
    default=str,
)}

YOLO DETECTION:
{json.dumps(
    detected_objects,
    indent=2,
    default=str,
)}

VERIFIED EMPLOYEE RAG KNOWLEDGE:
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

Generate only grounded municipal-worker guidance.

Do not add unsupported facts.
""".strip()