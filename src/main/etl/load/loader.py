"""Load stage: persist cleaned jobs into the job table."""

from __future__ import annotations

from typing import Any, Literal

from common import mysql_loader

LoadMode = Literal["insert", "update", "upsert"]

JOB_COLUMNS = (
    "source",
    "source_job_id",
    "company",
    "title",
    "role",
    "ctc_currency",
    "min_ctc",
    "max_ctc",
    "location",
    "work_mode",
    "job_type",
    "description",
    "application_url",
    "status",
    "posted_on",
)


def _to_job_row(record: dict[str, Any]) -> dict[str, Any]:
    return {column: record.get(column) for column in JOB_COLUMNS}


def load_jobs(
    records: list[dict[str, Any]],
    *,
    mode: LoadMode = "upsert",
    batch_size: int | None = None,
) -> dict[str, Any]:
    rows = [_to_job_row(record) for record in records]
    if not rows:
        return {"mode": mode, "attempted": 0, "affected": 0}

    with mysql_loader.engine.begin() as conn:
        if mode == "insert":
            affected = mysql_loader.insert_jobs(
                rows, batch_size=batch_size, connection=conn
            )
        elif mode == "update":
            affected = mysql_loader.update_jobs(
                rows, batch_size=batch_size, connection=conn
            )
        else:
            affected = mysql_loader.upsert_jobs(
                rows, batch_size=batch_size, connection=conn
            )

    return {"mode": mode, "attempted": len(rows), "affected": affected}
