import json
from datetime import datetime
from typing import Any
from uuid import uuid4

from db import execute, fetch_all, fetch_one
from repositories.employee_repository import (
    get_assignment_detection_session,
    get_employee_advice_by_id,
    get_employee_assignment,
    get_employee_assignments,
    get_employee_scope,
)
from services.employee_rag_service import (
    generate_employee_advice_offline,
)


# ============================================================
# DATABASE COPY HELPERS
# ============================================================

def get_table_columns(
    table_name: str,
) -> list[dict[str, Any]]:
    """Return column information for an allowed MySQL table."""

    allowed_tables = {
        "detection_sessions",
        "detected_objects",
    }

    if table_name not in allowed_tables:
        raise ValueError(
            f"Copying table '{table_name}' is not allowed."
        )

    return fetch_all(
        f"SHOW COLUMNS FROM `{table_name}`"
    )


def insert_copied_row(
    table_name: str,
    source_row: dict[str, Any],
    replacements: dict[str, Any],
) -> int:
    """
    Copy one row while replacing selected column values.

    Auto-increment and generated columns are skipped.
    """

    column_information = get_table_columns(
        table_name
    )

    insert_columns: list[str] = []
    insert_values: list[Any] = []

    for column in column_information:
        column_name = (
            column.get("Field")
            or column.get("field")
        )

        extra = str(
            column.get("Extra")
            or column.get("extra")
            or ""
        ).lower()

        if not column_name:
            continue

        if "auto_increment" in extra:
            continue

        if "generated" in extra:
            continue

        insert_columns.append(
            column_name
        )

        if column_name in replacements:
            insert_values.append(
                replacements[column_name]
            )
        else:
            insert_values.append(
                source_row.get(column_name)
            )

    formatted_columns = ", ".join(
        f"`{column_name}`"
        for column_name in insert_columns
    )

    placeholders = ", ".join(
        "%s"
        for _ in insert_columns
    )

    new_record_id = execute(
        f"""
        INSERT INTO `{table_name}` (
            {formatted_columns}
        )
        VALUES (
            {placeholders}
        )
        """,
        tuple(insert_values),
    )

    if not new_record_id:
        raise RuntimeError(
            f"The new {table_name} record "
            "could not be created."
        )

    return int(new_record_id)


# ============================================================
# FIND EMPLOYEE AND ASSIGNMENT
# ============================================================

def find_demo_employee() -> dict[str, Any]:
    """Find the first active employee under an approved authority."""

    employee_row = fetch_one(
        """
        SELECT
            e.employee_id

        FROM employees AS e

        JOIN users AS u
            ON u.user_id = e.user_id

        JOIN community_authorities AS ca
            ON ca.authority_id = e.authority_id

        WHERE e.employment_status = 'active'
          AND u.account_status = 'active'
          AND ca.approval_status = 'approved'

        ORDER BY e.employee_id

        LIMIT 1
        """
    )

    if employee_row is None:
        raise RuntimeError(
            "No active approved employee was found."
        )

    employee_id = int(
        employee_row["employee_id"]
    )

    employee = get_employee_scope(
        employee_id
    )

    if employee is None:
        raise RuntimeError(
            "The employee scope could not be loaded."
        )

    return employee


def find_demo_assignment(
    employee_id: int,
) -> dict[str, Any]:
    """Find one usable assignment belonging to the employee."""

    assignments = get_employee_assignments(
        employee_id=employee_id,
        limit=50,
    )

    allowed_statuses = {
        "assigned",
        "accepted",
        "in_progress",
        "completed",
    }

    for assignment_row in assignments:
        assignment_status = str(
            assignment_row.get(
                "assignment_status",
                "",
            )
        ).lower()

        if assignment_status not in allowed_statuses:
            continue

        assignment_id = int(
            assignment_row["assignment_id"]
        )

        assignment = get_employee_assignment(
            assignment_id=assignment_id,
            employee_id=employee_id,
        )

        if assignment is not None:
            return assignment

    raise RuntimeError(
        "No usable assignment was found for "
        "the selected employee."
    )


# ============================================================
# CREATE EMPLOYEE DEMO DETECTION
# ============================================================

def find_source_detection() -> dict[str, Any]:
    """
    Find an existing completed detection that has
    at least one detected object.
    """

    source_detection = fetch_one(
        """
        SELECT
            ds.*

        FROM detection_sessions AS ds

        WHERE ds.processing_status = 'completed'

          AND EXISTS (
              SELECT 1

              FROM detected_objects AS obj

              WHERE obj.detection_session_id =
                    ds.detection_session_id
          )

        ORDER BY
            ds.completed_at DESC,
            ds.detection_session_id DESC

        LIMIT 1
        """
    )

    if source_detection is None:
        raise RuntimeError(
            "No completed detection with detected objects "
            "was found. Run test_household_rag.py first."
        )

    return source_detection


def create_employee_demo_detection(
    employee: dict[str, Any],
    assignment: dict[str, Any],
) -> int:
    """
    Copy an existing completed detection and connect
    the copied session to the employee assignment report.
    """

    source_detection = find_source_detection()

    source_detection_id = int(
        source_detection[
            "detection_session_id"
        ]
    )

    source_objects = fetch_all(
        """
        SELECT
            *

        FROM detected_objects

        WHERE detection_session_id = %s

        ORDER BY detected_object_id
        """,
        (source_detection_id,),
    )

    if not source_objects:
        raise RuntimeError(
            "The source detection contains no objects."
        )

    current_time = datetime.now()

    session_replacements: dict[str, Any] = {
        "request_uuid": str(uuid4()),
        "user_id": int(employee["user_id"]),
        "report_id": int(assignment["report_id"]),
        "processing_status": "completed",
        "created_at": current_time,
        "completed_at": current_time,
    }

    if "source_module" in source_detection:
        session_replacements[
            "source_module"
        ] = "employee"

    if "original_filename" in source_detection:
        old_filename = str(
            source_detection.get(
                "original_filename"
            )
            or "waste.jpg"
        )

        session_replacements[
            "original_filename"
        ] = f"employee_demo_{old_filename}"

    new_detection_session_id = insert_copied_row(
        table_name="detection_sessions",
        source_row=dict(source_detection),
        replacements=session_replacements,
    )

    copied_object_count = 0

    for source_object in source_objects:
        object_replacements: dict[str, Any] = {
            "detection_session_id": (
                new_detection_session_id
            )
        }

        if "created_at" in source_object:
            object_replacements[
                "created_at"
            ] = current_time

        insert_copied_row(
            table_name="detected_objects",
            source_row=dict(source_object),
            replacements=object_replacements,
        )

        copied_object_count += 1

    print(
        "Created employee demo detection:",
        new_detection_session_id,
    )

    print(
        "Copied detected objects:",
        copied_object_count,
    )

    return new_detection_session_id


def ensure_assignment_detection(
    employee: dict[str, Any],
    assignment: dict[str, Any],
) -> dict[str, Any]:
    """
    Use an existing assignment detection or create
    a separate demo detection for the assignment.
    """

    employee_id = int(
        employee["employee_id"]
    )

    assignment_id = int(
        assignment["assignment_id"]
    )

    existing_detection = (
        get_assignment_detection_session(
            assignment_id=assignment_id,
            employee_id=employee_id,
        )
    )

    if existing_detection is not None:
        print(
            "Using existing assignment detection:",
            existing_detection[
                "detection_session_id"
            ],
        )

        return existing_detection

    print(
        "No completed detection is connected "
        "to this assignment."
    )

    print(
        "Creating a separate employee demo detection..."
    )

    create_employee_demo_detection(
        employee=employee,
        assignment=assignment,
    )

    new_detection = (
        get_assignment_detection_session(
            assignment_id=assignment_id,
            employee_id=employee_id,
        )
    )

    if new_detection is None:
        raise RuntimeError(
            "The demo detection was created, but it "
            "could not be retrieved for the assignment."
        )

    return new_detection


# ============================================================
# MAIN EMPLOYEE RAG TEST
# ============================================================

def run_employee_rag_test() -> None:
    """Run and verify the complete offline Employee RAG."""

    print("=" * 60)
    print("ECO-LENS EMPLOYEE RAG TEST")
    print("=" * 60)

    # Employee
    employee = find_demo_employee()

    employee_id = int(
        employee["employee_id"]
    )

    print("\n========== EMPLOYEE ==========")

    print(
        "Employee ID:",
        employee_id,
    )

    print(
        "Employee name:",
        employee.get("employee_name"),
    )

    print(
        "Employee code:",
        employee.get("employee_code"),
    )

    print(
        "Organization:",
        employee.get("organization_name"),
    )

    # Assignment
    assignment = find_demo_assignment(
        employee_id
    )

    assignment_id = int(
        assignment["assignment_id"]
    )

    print("\n========== ASSIGNMENT ==========")

    print(
        "Assignment ID:",
        assignment_id,
    )

    print(
        "Report ID:",
        assignment.get("report_id"),
    )

    print(
        "Report title:",
        assignment.get("report_title"),
    )

    print(
        "Assignment priority:",
        assignment.get(
            "assignment_priority"
        ),
    )

    print(
        "Assignment status:",
        assignment.get(
            "assignment_status"
        ),
    )

    # Detection
    print("\n========== DETECTION ==========")

    detection = ensure_assignment_detection(
        employee=employee,
        assignment=assignment,
    )

    print(
        "Detection session ID:",
        detection.get(
            "detection_session_id"
        ),
    )

    # Generate advice
    print("\n========== GENERATING ADVICE ==========")

    result = generate_employee_advice_offline(
        employee_id=employee_id,
        assignment_id=assignment_id,
        response_language="en",
    )

    advice_id = int(
        result["advice_id"]
    )

    response = result["result"]

    print(
        "Advice ID:",
        advice_id,
    )

    print(
        "Mode:",
        response["mode"],
    )

    print(
        "Overall priority:",
        response["overall_priority"],
    )

    print(
        "Instruction blocks:",
        len(response["work_instructions"]),
    )

    print(
        "Verified sources:",
        len(response["source_list"]),
    )

    print(
        "Verified facilities:",
        len(response["verified_facilities"]),
    )

    print(
        "Local verification required:",
        response[
            "local_verification_required"
        ],
    )

    # Instructions
    print("\n========== WORK INSTRUCTIONS ==========")

    for index, instruction in enumerate(
        response["work_instructions"],
        start=1,
    ):
        print(
            f"\nInstruction {index}"
        )

        print(
            "Waste class:",
            instruction["class_name"],
        )

        print(
            "Category:",
            instruction["category_name"],
        )

        print(
            "Priority:",
            instruction["priority"],
        )

        print(
            "Safety rule IDs:",
            instruction["safety_rule_ids"],
        )

        print(
            "Source IDs:",
            instruction["source_ids"],
        )

        print(
            "Facility IDs:",
            instruction["facility_ids"],
        )

        print(
            "Verified knowledge found:",
            instruction[
                "verified_knowledge_found"
            ],
        )

        print(
            "Human review required:",
            instruction[
                "human_review_required"
            ],
        )

    # Verify database save
    saved_advice = get_employee_advice_by_id(
        advice_id=advice_id,
        employee_id=employee_id,
    )

    if saved_advice is None:
        raise RuntimeError(
            "Employee advice was generated but "
            "could not be retrieved from MySQL."
        )

    print("\n========== SAVED ADVICE ==========")

    print(
        "Saved advice confirmed:",
        saved_advice["advice_id"],
    )

    print(
        "Saved prompt version:",
        saved_advice["prompt_version"],
    )

    # Final result
    print("\n========== TEST SUMMARY ==========")

    print(
        json.dumps(
            {
                "advice_id": advice_id,
                "employee_id": employee_id,
                "assignment_id": assignment_id,
                "detection_session_id": result[
                    "detection_session_id"
                ],
                "overall_priority": response[
                    "overall_priority"
                ],
                "summary": response["summary"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )

    print("\n" + "=" * 60)
    print("EMPLOYEE RAG TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    run_employee_rag_test()