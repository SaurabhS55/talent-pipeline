"""Shared MySQL engine and persistence helpers for raw_job / job tables."""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable, Sequence

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

from configs.settings import DATABASE_URL, LOAD_BATCH_SIZE

engine: Engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,
    pool_pre_ping=True,
)


def test_connection() -> bool:
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("DB connection successful:", result.scalar())
            return True
    except Exception as e:
        print("DB connection failed:", e)
        return False


def _json_default(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, set):
        return list(value)
    return str(value)


def _chunked(items: Sequence[Any], size: int) -> Iterable[Sequence[Any]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def insert_raw_jobs(
    records: Sequence[dict[str, Any]],
    *,
    batch_size: int | None = None,
    connection: Connection | None = None,
) -> int:
    if not records:
        return 0

    size = batch_size or LOAD_BATCH_SIZE
    sql = text(
        """
        INSERT INTO raw_job (source, source_job_id, payload)
        VALUES (:source, :source_job_id, CAST(:payload AS JSON))
        """
    )

    def _run(conn: Connection) -> int:
        inserted = 0
        for batch in _chunked(list(records), size):
            params = [
                {
                    "source": row["source"],
                    "source_job_id": row.get("source_job_id"),
                    "payload": json.dumps(row["payload"], default=_json_default),
                }
                for row in batch
            ]
            conn.execute(sql, params)
            inserted += len(params)
        return inserted

    if connection is not None:
        return _run(connection)

    with engine.begin() as conn:
        return _run(conn)


def insert_jobs(
    records: Sequence[dict[str, Any]],
    *,
    batch_size: int | None = None,
    connection: Connection | None = None,
) -> int:
    if not records:
        return 0

    size = batch_size or LOAD_BATCH_SIZE
    sql = text(
        """
        INSERT INTO job (
            source, source_job_id, company, title, role,
            ctc_currency, min_ctc, max_ctc, location, work_mode,
            job_type, description, application_url, status, posted_on
        ) VALUES (
            :source, :source_job_id, :company, :title, :role,
            :ctc_currency, :min_ctc, :max_ctc, :location, :work_mode,
            :job_type, :description, :application_url, :status, :posted_on
        )
        """
    )

    def _run(conn: Connection) -> int:
        inserted = 0
        for batch in _chunked(list(records), size):
            conn.execute(sql, list(batch))
            inserted += len(batch)
        return inserted

    if connection is not None:
        return _run(connection)

    with engine.begin() as conn:
        return _run(conn)


def update_jobs(
    records: Sequence[dict[str, Any]],
    *,
    batch_size: int | None = None,
    connection: Connection | None = None,
) -> int:
    if not records:
        return 0

    size = batch_size or LOAD_BATCH_SIZE
    sql = text(
        """
        UPDATE job SET
            company = :company,
            title = :title,
            role = :role,
            ctc_currency = :ctc_currency,
            min_ctc = :min_ctc,
            max_ctc = :max_ctc,
            location = :location,
            work_mode = :work_mode,
            job_type = :job_type,
            description = :description,
            application_url = :application_url,
            status = :status,
            posted_on = :posted_on,
            last_seen = CURRENT_TIMESTAMP
        WHERE source = :source AND source_job_id = :source_job_id
        """
    )

    def _run(conn: Connection) -> int:
        updated = 0
        for batch in _chunked(list(records), size):
            result = conn.execute(sql, list(batch))
            updated += result.rowcount or 0
        return updated

    if connection is not None:
        return _run(connection)

    with engine.begin() as conn:
        return _run(conn)


#upsert = insert or update
def upsert_jobs(
    records: Sequence[dict[str, Any]],
    *,
    batch_size: int | None = None,
    connection: Connection | None = None,
) -> int:
    if not records:
        return 0

    size = batch_size or LOAD_BATCH_SIZE
    sql = text(
        """
        INSERT INTO job (
            source, source_job_id, company, title, role,
            ctc_currency, min_ctc, max_ctc, location, work_mode,
            job_type, description, application_url, status, posted_on
        ) VALUES (
            :source, :source_job_id, :company, :title, :role,
            :ctc_currency, :min_ctc, :max_ctc, :location, :work_mode,
            :job_type, :description, :application_url, :status, :posted_on
        )
        ON DUPLICATE KEY UPDATE
            company = VALUES(company),
            title = VALUES(title),
            role = VALUES(role),
            ctc_currency = VALUES(ctc_currency),
            min_ctc = VALUES(min_ctc),
            max_ctc = VALUES(max_ctc),
            location = VALUES(location),
            work_mode = VALUES(work_mode),
            job_type = VALUES(job_type),
            description = VALUES(description),
            application_url = VALUES(application_url),
            status = VALUES(status),
            posted_on = COALESCE(VALUES(posted_on), job.posted_on),
            last_seen = CURRENT_TIMESTAMP
        """
    )

    def _run(conn: Connection) -> int:
        affected = 0
        for batch in _chunked(list(records), size):
            result = conn.execute(sql, list(batch))
            affected += result.rowcount or 0
        return affected

    if connection is not None:
        return _run(connection)

    with engine.begin() as conn:
        return _run(conn)


def fetch_unprocessed_raw_jobs(limit: int = 500) -> list[dict[str, Any]]:
    sql = text(
        """
        SELECT id, source, source_job_id, payload, fetched_at
        FROM raw_job
        ORDER BY id DESC
        LIMIT :limit
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, {"limit": limit}).mappings().all()
    results: list[dict[str, Any]] = []
    for row in rows:
        payload = row["payload"]
        if isinstance(payload, (bytes, bytearray)):
            payload = payload.decode("utf-8")
        if isinstance(payload, str):
            payload = json.loads(payload)
        results.append(
            {
                "id": row["id"],
                "source": row["source"],
                "source_job_id": row["source_job_id"],
                "payload": payload,
                "fetched_at": row["fetched_at"],
            }
        )
    return results
