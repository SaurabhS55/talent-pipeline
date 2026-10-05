"""Extract stage: JobSpy -> raw_job shaped records."""

from __future__ import annotations

from typing import Any

import pandas as pd

from etl.extract.job_scraper import scrape_job_listings


def _clean_str(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    return text or None

#serialize a JobSpy row into a JSON payload
def _row_to_payload(row: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, float) and pd.isna(value):
            payload[key] = None
        elif hasattr(value, "isoformat"):
            payload[key] = value.isoformat()
        elif isinstance(value, (list, dict, str, int, float, bool)) or value is None:
            payload[key] = value
        else:
            payload[key] = str(value)
    return payload


def extract_raw_jobs() -> list[dict[str, Any]]:
    frame = scrape_job_listings()
    if frame is None or frame.empty:
        return []

    records: list[dict[str, Any]] = []
    for row in frame.to_dict(orient="records"):
        source = _clean_str(row.get("site")) or "unknown"
        source_job_id = _clean_str(row.get("id")) or _clean_str(row.get("job_url"))
        records.append(
            {
                "source": source,
                "source_job_id": source_job_id,
                "payload": _row_to_payload(row),
            }
        )
    return records
