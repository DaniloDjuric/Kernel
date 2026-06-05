"""Load / save daily JSON archives."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from app_records import DayRecord

ARCHIVE_DIR = Path(__file__).resolve().parent / "data" / "archive"
ARCHIVE_DATE_FMT = "%d-%m-%Y"


def format_archive_date(work_date: date) -> str:
    return work_date.strftime(ARCHIVE_DATE_FMT)


def parse_archive_date(text: str) -> date | None:
    try:
        return datetime.strptime(text, ARCHIVE_DATE_FMT).date()
    except ValueError:
        return None


def archive_path(work_date: date) -> Path:
    return ARCHIVE_DIR / f"{format_archive_date(work_date)}.json"


def is_day_saved(work_date: date) -> bool:
    return archive_path(work_date).exists()


def list_archived_dates() -> list[date]:
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    dates: list[date] = []
    for path in ARCHIVE_DIR.glob("*.json"):
        parsed = parse_archive_date(path.stem)
        if parsed is not None:
            dates.append(parsed)
    return sorted(dates, reverse=True)


def load_day(work_date: date, employee_names: list[str]) -> dict[str, DayRecord]:
    records = {name: DayRecord() for name in employee_names}
    path = archive_path(work_date)
    if not path.exists():
        return records

    payload = json.loads(path.read_text(encoding="utf-8"))
    by_name = {row["ime"]: row for row in payload.get("zaposleni", [])}
    for name in employee_names:
        row = by_name.get(name)
        if row:
            records[name] = DayRecord.from_export_row(row, work_date)
    return records


def save_day(
    work_date: date,
    records: dict[str, DayRecord],
    employee_names: list[str],
    *,
    only_active: bool = True,
) -> Path:
    from employees import expected_minutes, schedule_label

    to_save = employee_names
    if only_active:
        to_save = [n for n in employee_names if records[n].has_activity()]

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "datum": format_archive_date(work_date),
        "zaposleni": [
            records[n].to_export_dict(
                n,
                expected=expected_minutes(n),
                raspored=schedule_label(n),
            )
            for n in to_save
        ],
        "izmijenjeno": datetime.now().isoformat(timespec="seconds"),
    }
    path = archive_path(work_date)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
