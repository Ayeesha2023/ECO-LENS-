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
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def _resolve_weight_path(weight_path: str) -> Path:
    path = Path(weight_path)
    if path.is_absolute():
        return path

    project_candidate = PROJECT_ROOT / path
    if project_candidate.exists():
        return project_candidate

    backend_candidate = BACKEND_DIR / path
    if backend_candidate.exists():
        return backend_candidate

    raise FileNotFoundError(
        f"YOLO model weight was not found: {weight_path}"
    )


@lru_cache(maxsize=2)
def _load_model(weight_path: str):
    resolved = _resolve_weight_path(weight_path)
    return YOLO(str(resolved))


def _current_model(cursor):
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
        raise ValueError("No deployable current YOLO model is configured.")
    return model_info


def _class_configuration(cursor, model_version_id: int, global_threshold: float):
    cursor.execute(
        """
        SELECT
            mc.model_class_id,
            mc.class_name,
            mc.display_name,
            COALESCE(it.confidence_threshold, %s) AS class_threshold
        FROM model_classes AS mc
        LEFT JOIN inference_thresholds AS it
            ON it.model_class_id = mc.model_class_id
           AND it.model_version_id = %s
        WHERE mc.is_active = 1
        ORDER BY mc.model_class_id
        """,
        (global_threshold, model_version_id),
    )
    rows = cursor.fetchall()

    lookup = {}
    threshold_by_id = {}

    for row in rows:
        lookup[_normalize_name(row["class_name"])] = row
        lookup[_normalize_name(row["display_name"])] = row
        threshold_by_id[int(row["model_class_id"])] = float(row["class_threshold"])

    return lookup, rows, threshold_by_id


def run_household_detection(
    *,
    user_id: int,
    original_filename: str,
    stored_image_path: Path,
):
    started = time.perf_counter()
    connection = _get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        connection.start_transaction()

        model_info = _current_model(cursor)
        global_threshold = float(model_info["global_confidence_threshold"])

        class_lookup, ordered_classes, threshold_by_id = _class_configuration(
            cursor,
            int(model_info["model_version_id"]),
            global_threshold,
        )

        # Run YOLO at the lowest configured threshold, then enforce each
        # class's own threshold before saving a detection.
        inference_threshold = min(
            [global_threshold, *threshold_by_id.values()]
        )

        model = _load_model(model_info["weight_path"])
        request_uuid = str(uuid.uuid4())
        relative_original = stored_image_path.relative_to(BACKEND_DIR).as_posix()

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
            VALUES (%s, %s, NULL, %s, 'household', %s, %s, %s, 'processing')
            """,
            (
                request_uuid,
                user_id,
                model_info["model_version_id"],
                original_filename,
                relative_original,
                global_threshold,
            ),
        )
        detection_session_id = int(cursor.lastrowid)

        results = model(
            str(stored_image_path),
            conf=inference_threshold,
            verbose=False,
        )
        result = results[0]

        annotated_name = f"{stored_image_path.stem}_annotated.jpg"
        annotated_path = stored_image_path.parent / annotated_name
        result.save(filename=str(annotated_path))
        relative_annotated = annotated_path.relative_to(BACKEND_DIR).as_posix()

        detected_objects = []

        if result.boxes is not None:
            for box in result.boxes:
                class_index = int(box.cls[0].item())
                confidence = float(box.conf[0].item())
                model_name = str(model.names[class_index])

                mapping = class_lookup.get(_normalize_name(model_name))

                # Safe fallback for the known 10-class EcoLens model when
                # class ordering matches model_classes.model_class_id order.
                if mapping is None and 0 <= class_index < len(ordered_classes):
                    mapping = ordered_classes[class_index]

                if mapping is None:
                    raise ValueError(
                        "YOLO class could not be mapped to model_classes: "
                        f"{model_name}"
                    )

                model_class_id = int(mapping["model_class_id"])
                class_threshold = float(
                    threshold_by_id.get(model_class_id, global_threshold)
                )

                if confidence < class_threshold:
                    continue

                xyxy = box.xyxy[0].cpu().tolist()

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
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        detection_session_id,
                        model_class_id,
                        confidence,
                        class_threshold,
                        float(xyxy[0]),
                        float(xyxy[1]),
                        float(xyxy[2]),
                        float(xyxy[3]),
                    ),
                )

                detected_objects.append(
                    {
                        "model_class_id": model_class_id,
                        "class_name": mapping["display_name"],
                        "confidence": round(confidence, 4),
                        "class_threshold": round(class_threshold, 4),
                    }
                )

        processing_time_ms = int((time.perf_counter() - started) * 1000)

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
            "detection_session_id": detection_session_id,
            "request_uuid": request_uuid,
            "model_version": model_info["version_name"],
            "architecture": model_info["architecture"],
            "global_confidence_threshold": global_threshold,
            "inference_threshold": inference_threshold,
            "detected_objects": detected_objects,
            "stored_image_path": relative_original,
            "annotated_image_path": relative_annotated,
            "processing_time_ms": processing_time_ms,
        }

    except Exception as exc:
        connection.rollback()
        raise exc

    finally:
        cursor.close()
        connection.close()