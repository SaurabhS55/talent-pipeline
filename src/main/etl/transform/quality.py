"""Data quality checks for transformed job records."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


REQUIRED_FIELDS = ("source", "source_job_id", "title")


@dataclass
class QualityReport:
    input_count: int = 0
    valid_count: int = 0
    invalid_count: int = 0
    duplicate_count: int = 0
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "input_count": self.input_count,
            "valid_count": self.valid_count,
            "invalid_count": self.invalid_count,
            "duplicate_count": self.duplicate_count,
            "error_count": len(self.errors),
            "errors": self.errors[:50],
        }


def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def validate_record(record: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for field_name in REQUIRED_FIELDS:
        if _is_blank(record.get(field_name)):
            issues.append(f"missing:{field_name}")

    title = record.get("title")
    if isinstance(title, str) and len(title) > 500:
        issues.append("title:too_long")

    min_ctc = record.get("min_ctc")
    max_ctc = record.get("max_ctc")
    if min_ctc is not None and max_ctc is not None:
        try:
            if float(min_ctc) > float(max_ctc):
                issues.append("salary:min_gt_max")
        except (TypeError, ValueError):
            issues.append("salary:invalid")

    work_mode = record.get("work_mode")
    if work_mode not in (None, "IN_OFFICE", "HYBRID", "REMOTE"):
        issues.append("work_mode:invalid")

    job_type = record.get("job_type")
    if job_type not in (
        None,
        "INTERNSHIP",
        "PART_TIME",
        "FULL_TIME",
        "FREELANCER",
        "CONTRACTOR",
    ):
        issues.append("job_type:invalid")

    status = record.get("status")
    if status not in (None, "ACTIVE", "CLOSED", "UNKNOWN"):
        issues.append("status:invalid")

    return issues


def fill_missing_values(record: dict[str, Any]) -> dict[str, Any]:
    filled = dict(record)
    if _is_blank(filled.get("status")):
        filled["status"] = "UNKNOWN"
    if _is_blank(filled.get("company")):
        filled["company"] = None
    if _is_blank(filled.get("location")):
        filled["location"] = None
    if _is_blank(filled.get("application_url")):
        filled["application_url"] = None
    if _is_blank(filled.get("description")):
        filled["description"] = None
    return filled


def deduplicate_records(
    records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, Any]] = []
    duplicates = 0
    for record in records:
        key = (
            str(record.get("source") or "").lower(),
            str(record.get("source_job_id") or "").lower(),
        )
        if key in seen or not key[1]:
            duplicates += 1
            continue
        seen.add(key)
        unique.append(record)
    return unique, duplicates


def apply_quality_checks(
    records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], QualityReport]:
    report = QualityReport(input_count=len(records))
    valid: list[dict[str, Any]] = []

    for record in records:
        try:
            candidate = fill_missing_values(record)
            issues = validate_record(candidate)
            if issues:
                report.invalid_count += 1
                report.errors.append(
                    f"{candidate.get('source')}:{candidate.get('source_job_id')} -> "
                    + ",".join(issues)
                )
                continue
            valid.append(candidate)
        except Exception as exc:  # noqa: BLE001 - collect and continue
            report.invalid_count += 1
            report.errors.append(f"exception:{exc}")

    deduped, duplicate_count = deduplicate_records(valid)
    report.duplicate_count = duplicate_count
    report.valid_count = len(deduped)
    return deduped, report
