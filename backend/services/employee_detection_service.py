import os
import re
import time
import uuid
from functools import lru_cache
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv
from ultralytics import YOLO


load_dotenv()


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent

UPLOAD_DIR = (
    BACKEND_DIR /
    "uploads" /
    "detections" /
    "employee"
)

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


def _get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "eco-lens_db"),
        autocommit=False,
    )


def _normalize_name(value: str) -> str:
    return re.sub(
        r"[^a-z0-9]+",
        "",
        str(value).lower(),
    )


def _resolve_weight_path(
    weight_path: str,
) -> Path:
    path = Path(weight_path)

    if path.is_absolute():
        return path

    # DB currently stores paths such as:
    # backend/models/best.pt
    project_candidate = (
        PROJECT_ROOT /
        path
    )

    if project_candidate.exists():
        return project_candidate

    backend_candidate = (
        BACKEND_DIR /
        path
    )

    if backend_candidate.exists():
        return backend_candidate

    raise FileNotFoundError(
        "YOLO model weight was not found: "
        f"{weight_path}"
    )


@lru_cache(maxsize=2)
def _load_model(
    weight_path: str,
):
    resolved = _resolve_weight_path(
        weight_path
    )

    return YOLO(
        str(resolved)
    )


def _current_model(
    cursor,
):
    cursor.execute(
        """
        SELECT
            model_version_id,
            version_name,
            architecture,
            weight_path,
            global_confidence_threshold

        FROM model_versions

        WHERE is_current_deployment = 1
          AND artifact_status = 'available'

        ORDER BY model_version_id DESC

        LIMIT 1
        """
    )

    model_info = cursor.fetchone()

    if model_info is None:
        raise ValueError(
            "No deployable current YOLO model is configured."
        )

    return model_info


def _class_lookup(
    cursor,
):
    cursor.execute(
        """
        SELECT
            model_class_id,
            class_name,
            display_name

        FROM model_classes

        WHERE is_active = 1

        ORDER BY model_class_id
        """
    )

    rows = cursor.fetchall()

    lookup = {}

    for row in rows:
        lookup[
            _normalize_name(
                row["class_name"]
            )
        ] = row

        lookup[
            _normalize_name(
                row["display_name"]
            )
        ] = row

    return lookup, rows


def run_employee_detection(
    *,
    user_id: int,
    report_id: int,
    original_filename: str,
    stored_image_path: Path,
):
    started = time.perf_counter()

    connection = _get_connection()

    cursor = connection.cursor(
        dictionary=True
    )

    try:
        connection.start_transaction()

        model_info = _current_model(
            cursor
        )

        threshold = float(
            model_info[
                "global_confidence_threshold"
            ]
        )

        model = _load_model(
            model_info["weight_path"]
        )

        (
            class_lookup,
            ordered_classes,
        ) = _class_lookup(
            cursor
        )

        request_uuid = str(
            uuid.uuid4()
        )

        relative_original = (
            stored_image_path
            .relative_to(
                BACKEND_DIR
            )
            .as_posix()
        )

        cursor.execute(
            """
            INSERT INTO detection_sessions (
                request_uuid,
                user_id,
                report_id,
                model_version_id,
                source_module,
                original_filename,
                stored_image_path,
                applied_global_threshold,
                processing_status
            )
            VALUES (
                %s,
                %s,
                %s,
                %s,
                'employee',
                %s,
                %s,
                %s,
                'processing'
            )
            """,
            (
                request_uuid,
                user_id,
                report_id,
                model_info[
                    "model_version_id"
                ],
                original_filename,
                relative_original,
                threshold,
            ),
        )

        detection_session_id = int(
            cursor.lastrowid
        )

        results = model(
            str(stored_image_path),
            conf=threshold,
            verbose=False,
        )

        result = results[0]

        annotated_name = (
            f"{stored_image_path.stem}"
            "_annotated.jpg"
        )

        annotated_path = (
            stored_image_path.parent /
            annotated_name
        )

        result.save(
            filename=str(
                annotated_path
            )
        )

        relative_annotated = (
            annotated_path
            .relative_to(
                BACKEND_DIR
            )
            .as_posix()
        )

        detected_objects = []

        if result.boxes is not None:
            for box in result.boxes:
                class_index = int(
                    box.cls[0].item()
                )

                confidence = float(
                    box.conf[0].item()
                )

                model_name = str(
                    model.names[
                        class_index
                    ]
                )

                mapping = class_lookup.get(
                    _normalize_name(
                        model_name
                    )
                )

                # Fallback for a model whose class
                # order matches the DB's 10 classes.
                if (
                    mapping is None
                    and
                    0 <= class_index <
                    len(ordered_classes)
                ):
                    mapping = (
                        ordered_classes[
                            class_index
                        ]
                    )

                if mapping is None:
                    raise ValueError(
                        "YOLO class could not be mapped "
                        f"to model_classes: {model_name}"
                    )

                xyxy = (
                    box.xyxy[0]
                    .cpu()
                    .tolist()
                )

                cursor.execute(
                    """
                    INSERT INTO detected_objects (
                        detection_session_id,
                        model_class_id,
                        confidence,
                        applied_class_threshold,
                        bbox_x1,
                        bbox_y1,
                        bbox_x2,
                        bbox_y2
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                    """,
                    (
                        detection_session_id,
                        mapping[
                            "model_class_id"
                        ],
                        confidence,
                        threshold,
                        float(xyxy[0]),
                        float(xyxy[1]),
                        float(xyxy[2]),
                        float(xyxy[3]),
                    ),
                )

                detected_objects.append(
                    {
                        "model_class_id":
                            int(
                                mapping[
                                    "model_class_id"
                                ]
                            ),

                        "class_name":
                            mapping[
                                "display_name"
                            ],

                        "confidence":
                            round(
                                confidence,
                                4,
                            ),
                    }
                )

        processing_time_ms = int(
            (
                time.perf_counter()
                - started
            )
            * 1000
        )

        cursor.execute(
            """
            UPDATE detection_sessions

            SET
                annotated_image_path = %s,
                processing_status = 'completed',
                processing_time_ms = %s,
                completed_at = NOW()

            WHERE detection_session_id = %s
            """,
            (
                relative_annotated,
                processing_time_ms,
                detection_session_id,
            ),
        )

        connection.commit()

        return {
            "detection_session_id":
                detection_session_id,

            "request_uuid":
                request_uuid,

            "model_version":
                model_info[
                    "version_name"
                ],

            "architecture":
                model_info[
                    "architecture"
                ],

            "confidence_threshold":
                threshold,

            "detected_objects":
                detected_objects,

            "stored_image_path":
                relative_original,

            "annotated_image_path":
                relative_annotated,

            "processing_time_ms":
                processing_time_ms,
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()