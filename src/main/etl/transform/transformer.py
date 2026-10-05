"""Transform helpers: text, dates, location, salary, skills."""

from __future__ import annotations

import html
import re
import unicodedata
from datetime import datetime
from typing import Any

from dateutil import parser as date_parser

JOB_TYPE_MAP = {
    "fulltime": "FULL_TIME",
    "full_time": "FULL_TIME",
    "full-time": "FULL_TIME",
    "parttime": "PART_TIME",
    "part_time": "PART_TIME",
    "part-time": "PART_TIME",
    "internship": "INTERNSHIP",
    "intern": "INTERNSHIP",
    "contract": "CONTRACTOR",
    "contractor": "CONTRACTOR",
    "freelance": "FREELANCER",
    "freelancer": "FREELANCER",
}

CITY_ALIASES = {
    "bangalore": "Bengaluru",
    "bengaluru": "Bengaluru",
    "bom": "Mumbai",
    "bombay": "Mumbai",
    "mumbai": "Mumbai",
    "delhi": "Delhi",
    "new delhi": "New Delhi",
    "gurgaon": "Gurugram",
    "gurugram": "Gurugram",
    "madras": "Chennai",
    "chennai": "Chennai",
    "hyd": "Hyderabad",
    "hyderabad": "Hyderabad",
    "pune": "Pune",
    "calcutta": "Kolkata",
    "kolkata": "Kolkata",
    "sf": "San Francisco",
    "san francisco": "San Francisco",
    "nyc": "New York",
    "new york": "New York",
    "remote": "Remote",
}

SKILL_KEYWORDS = [
    "python",
    "java",
    "javascript",
    "typescript",
    "react",
    "node.js",
    "nodejs",
    "sql",
    "mysql",
    "postgresql",
    "mongodb",
    "aws",
    "azure",
    "gcp",
    "docker",
    "kubernetes",
    "kafka",
    "spark",
    "hadoop",
    "airflow",
    "dbt",
    "snowflake",
    "pandas",
    "numpy",
    "fastapi",
    "django",
    "flask",
    "spring",
    "golang",
    "go",
    "rust",
    "c++",
    "c#",
    "scala",
    "terraform",
    "linux",
    "git",
    "ci/cd",
    "machine learning",
    "deep learning",
    "nlp",
    "llm",
    "pytorch",
    "tensorflow",
]


def clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    text = html.unescape(text)
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"[\r\t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ ]{2,}", " ", text)
    text = text.strip()
    return text or None


def normalize_date(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    try:
        parsed = date_parser.parse(str(value), fuzzy=True)
        return parsed.replace(tzinfo=None)
    except (ValueError, OverflowError, TypeError):
        return None


def normalize_location(value: Any) -> str | None:
    text = clean_text(value)
    if not text:
        return None

    lowered = text.lower()
    for alias, canonical in CITY_ALIASES.items():
        if alias in lowered:
            # Keep extra context when present (e.g. "Bengaluru, Karnataka")
            parts = [p.strip() for p in re.split(r"[,|/]", text) if p.strip()]
            if len(parts) <= 1:
                return canonical
            normalized_parts = [canonical]
            normalized_parts.extend(part.title() for part in parts[1:])
            return ", ".join(normalized_parts)

    return text.title() if text.isupper() or text.islower() else text


def parse_salary(
    payload: dict[str, Any],
) -> tuple[float | None, float | None, str | None]:
    min_amount = payload.get("min_amount")
    max_amount = payload.get("max_amount")
    currency = clean_text(payload.get("currency"))
    interval = (clean_text(payload.get("interval")) or "").lower()

    def _to_float(raw: Any) -> float | None:
        if raw is None or raw == "":
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    min_ctc = _to_float(min_amount)
    max_ctc = _to_float(max_amount)

    # Normalize common intervals to approximate annual CTC
    multipliers = {
        "hourly": 2080,
        "daily": 260,
        "weekly": 52,
        "monthly": 12,
        "yearly": 1,
        "annual": 1,
    }
    factor = multipliers.get(interval)
    if factor and factor != 1:
        if min_ctc is not None:
            min_ctc *= factor
        if max_ctc is not None:
            max_ctc *= factor

    if currency:
        currency = currency.upper()[:3]

    # Fallback: parse free-text salary snippets from description/title
    if min_ctc is None and max_ctc is None:
        blob = " ".join(
            filter(
                None,
                [
                    clean_text(payload.get("title")),
                    clean_text(payload.get("description")),
                ],
            )
        )
        match = re.search(
            r"(₹|rs\.?|inr|usd|\$)\s?([\d,]+(?:\.\d+)?)\s*(?:-|to|–)\s*"
            r"([\d,]+(?:\.\d+)?)\s*(lpa|lakh|lakhs|k|lac)?",
            blob,
            flags=re.I,
        )
        if match:
            cur_raw, low, high, unit = match.groups()
            min_ctc = float(low.replace(",", ""))
            max_ctc = float(high.replace(",", ""))
            unit = (unit or "").lower()
            if unit in {"lpa", "lakh", "lakhs", "lac"}:
                min_ctc *= 100_000
                max_ctc *= 100_000
            elif unit == "k":
                min_ctc *= 1_000
                max_ctc *= 1_000
            if "$" in cur_raw or cur_raw.lower() == "usd":
                currency = "USD"
            else:
                currency = currency or "INR"

    if min_ctc is not None and max_ctc is not None and min_ctc > max_ctc:
        min_ctc, max_ctc = max_ctc, min_ctc

    return min_ctc, max_ctc, currency


def extract_skills(payload: dict[str, Any]) -> list[str]:
    explicit = payload.get("skills")
    found: list[str] = []
    if isinstance(explicit, list):
        found.extend(clean_text(s) for s in explicit if clean_text(s))
    elif isinstance(explicit, str) and explicit.strip():
        found.extend(
            s for s in (clean_text(p) for p in re.split(r"[,|/]", explicit)) if s
        )

    blob = " ".join(
        filter(
            None,
            [
                clean_text(payload.get("title")),
                clean_text(payload.get("description")),
                " ".join(found),
            ],
        )
    ).lower()

    for skill in SKILL_KEYWORDS:
        if skill in blob:
            label = skill if skill != "nodejs" else "node.js"
            if label not in {s.lower() for s in found}:
                found.append(label)

    # Deduplicate preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for skill in found:
        key = skill.lower()
        if key not in seen:
            seen.add(key)
            unique.append(skill)
    return unique[:25]


def map_job_type(raw: Any) -> str | None:
    if raw is None:
        return None
    values = raw if isinstance(raw, list) else str(raw).split(",")
    for value in values:
        mapped = JOB_TYPE_MAP.get(str(value).strip().lower())
        if mapped:
            return mapped
    return None


def map_work_mode(payload: dict[str, Any]) -> str | None:
    wfh = clean_text(payload.get("work_from_home_type"))
    if wfh:
        lowered = wfh.lower()
        if "remote" in lowered:
            return "REMOTE"
        if "hybrid" in lowered:
            return "HYBRID"
        if "office" in lowered or "wfo" in lowered:
            return "IN_OFFICE"

    location = (clean_text(payload.get("location")) or "").lower()
    if "remote" in location:
        return "REMOTE"

    is_remote = payload.get("is_remote")
    if is_remote is True:
        return "REMOTE"
    if is_remote is False:
        return "IN_OFFICE"
    return None


def transform_raw_record(raw: dict[str, Any]) -> dict[str, Any]:
    payload = raw.get("payload") if "payload" in raw else raw
    if not isinstance(payload, dict):
        payload = {}

    source = clean_text(raw.get("source") or payload.get("site")) or "unknown"
    source_job_id = (
        clean_text(raw.get("source_job_id"))
        or clean_text(payload.get("id"))
        or clean_text(payload.get("job_url"))
        or ""
    )

    title = clean_text(payload.get("title")) or ""
    description = clean_text(payload.get("description"))
    skills = extract_skills(payload)
    min_ctc, max_ctc, currency = parse_salary(payload)

    # Persist extracted skills in role when job_function is absent
    role = clean_text(payload.get("job_function"))
    if not role and skills:
        role = ", ".join(skills[:5])

    return {
        "raw_id": raw.get("id"),
        "source": source,
        "source_job_id": source_job_id,
        "company": clean_text(payload.get("company")),
        "title": title,
        "role": role,
        "ctc_currency": currency,
        "min_ctc": min_ctc,
        "max_ctc": max_ctc,
        "location": normalize_location(payload.get("location")),
        "work_mode": map_work_mode(payload),
        "job_type": map_job_type(payload.get("job_type")),
        "description": description,
        "application_url": clean_text(payload.get("job_url_direct"))
        or clean_text(payload.get("job_url")),
        "status": "ACTIVE",
        "posted_on": normalize_date(payload.get("date_posted")),
        "skills": skills,
    }


def transform_records(raw_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [transform_raw_record(raw) for raw in raw_records]
