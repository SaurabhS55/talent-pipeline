"""End-to-end talent pipeline orchestration."""

from __future__ import annotations

from typing import Any

from common import mysql_loader
from configs import settings
from etl.extract.extractor import extract_raw_jobs
from etl.load.loader import load_jobs
from etl.transform.quality import apply_quality_checks
from etl.transform.transformer import transform_records


def run_extract_and_stage_raw() -> dict[str, Any]:
    raw_records = extract_raw_jobs()
    inserted = mysql_loader.insert_raw_jobs(raw_records)
    return {
        "extracted": len(raw_records),
        "raw_inserted": inserted,
        "raw_records": raw_records,
    }


def run_transform_quality_load(
    raw_records: list[dict[str, Any]] | None = None,
    *,
    load_mode: str = "upsert",
    raw_limit: int | None = None,
) -> dict[str, Any]:
    if raw_records is None:
        raw_records = mysql_loader.fetch_unprocessed_raw_jobs(
            limit=raw_limit or settings.TRANSFORM_RAW_LIMIT
        )

    transformed = transform_records(raw_records)
    cleaned, quality = apply_quality_checks(transformed)
    load_result = load_jobs(cleaned, mode=load_mode)  # type: ignore[arg-type]

    return {
        "raw_read": len(raw_records),
        "transformed": len(transformed),
        "quality": quality.as_dict(),
        "load": load_result,
    }


def run_pipeline() -> dict[str, Any]:
    """Extract -> raw_job -> transform/quality -> upsert job."""
    if not mysql_loader.test_connection():
        raise RuntimeError("Database connection failed")

    extract_result = run_extract_and_stage_raw()
    transform_result = run_transform_quality_load(
        extract_result["raw_records"],
        load_mode="upsert",
    )
    return {
        "extract": {
            "extracted": extract_result["extracted"],
            "raw_inserted": extract_result["raw_inserted"],
        },
        "transform_load": {
            "raw_read": transform_result["raw_read"],
            "transformed": transform_result["transformed"],
            "quality": transform_result["quality"],
            "load": transform_result["load"],
        },
    }
