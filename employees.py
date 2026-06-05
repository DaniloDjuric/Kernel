from __future__ import annotations
from enum import Enum

class DailySchedule(Enum):
    FOUR_HOURS = 4*60           # Četiri sata
    SIX_HOURS_40 = 6*60 + 40    # Šest sati i četrdeset minuta
    EIGHT_HOURS = 8*60          # Osam sati
SCHEDULE_LABELS: dict[DailySchedule, str] = {
    DailySchedule.FOUR_HOURS: "4h",
    DailySchedule.SIX_HOURS_40: "6h 40m",
    DailySchedule.EIGHT_HOURS: "8h",
}


"""Zaposleni i koliko sati rade."""
EMPLOYEES_CONFIG: list[tuple[str, DailySchedule]] = [

    # Dodavanje ili uklanjanje zaposlenih ovjde.
    # Redoslijed je redoslijed prikaza u aplikaciji.

    ("Neđo", DailySchedule.EIGHT_HOURS),
    ("Danilo M.", DailySchedule.FOUR_HOURS),
    ("Nino", DailySchedule.EIGHT_HOURS),
    ("Enđel", DailySchedule.SIX_HOURS_40),
    ("Danilo Đ.", DailySchedule.SIX_HOURS_40),
    # ("Ime Prezime", DailySchedule.SIX_HOURS_40),
]


# Testovi:
EMPLOYEES: list[str] = [name for name, _ in EMPLOYEES_CONFIG]
SCHEDULE_BY_EMPLOYEE: dict[str, DailySchedule] = dict(EMPLOYEES_CONFIG)
def _validate_config() -> None:
    if len(EMPLOYEES) < 1:
        raise ValueError("employees.py: EMPLOYEES_CONFIG must have at least one worker.")
    if len(EMPLOYEES) != len(set(EMPLOYEES)):
        raise ValueError("employees.py: duplicate names in EMPLOYEES_CONFIG.")
_validate_config()

def expected_minutes(employee_name: str) -> int:
    return SCHEDULE_BY_EMPLOYEE[employee_name].value
def schedule_label(employee_name: str) -> str:
    return SCHEDULE_LABELS[SCHEDULE_BY_EMPLOYEE[employee_name]]
