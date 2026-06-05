"""Data models for one employee's shift on one day."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum, auto

STEP_FIELDS = ("dolazak", "pocetak_pauze", "kraj_pauze", "kraj_smjene")


class ShiftStep(Enum):
    DOLAZAK = auto()
    POCETAK_PAUZE = auto()
    KRAJ_PAUZE = auto()
    KRAJ_SMJENE = auto()
    DONE = auto()


STEP_LABELS = {
    ShiftStep.DOLAZAK: "Dolazak",
    ShiftStep.POCETAK_PAUZE: "Početak pauze",
    ShiftStep.KRAJ_PAUZE: "Kraj pauze",
    ShiftStep.KRAJ_SMJENE: "Kraj smjene",
}

STEP_TO_FIELD = {
    ShiftStep.DOLAZAK: "dolazak",
    ShiftStep.POCETAK_PAUZE: "pocetak_pauze",
    ShiftStep.KRAJ_PAUZE: "kraj_pauze",
    ShiftStep.KRAJ_SMJENE: "kraj_smjene",
}

FIELD_TO_STEP = {v: k for k, v in STEP_TO_FIELD.items()}


@dataclass
class DayRecord:
    dolazak: datetime | None = None
    pocetak_pauze: datetime | None = None
    kraj_pauze: datetime | None = None
    kraj_smjene: datetime | None = None

    def get(self, step: ShiftStep) -> datetime | None:
        return getattr(self, STEP_TO_FIELD[step])

    def set(self, step: ShiftStep, when: datetime | None) -> None:
        setattr(self, STEP_TO_FIELD[step], when)

    def next_step(self) -> ShiftStep:
        if self.dolazak is None:
            return ShiftStep.DOLAZAK
        if self.pocetak_pauze is None:
            return ShiftStep.POCETAK_PAUZE
        if self.kraj_pauze is None:
            return ShiftStep.KRAJ_PAUZE
        if self.kraj_smjene is None:
            return ShiftStep.KRAJ_SMJENE
        return ShiftStep.DONE

    def apply(self, step: ShiftStep, when: datetime) -> None:
        self.set(step, when)

    def has_activity(self) -> bool:
        return self.dolazak is not None

    @staticmethod
    def format_time(when: datetime | None) -> str:
        return when.strftime("%H:%M") if when else "—"

    @staticmethod
    def parse_time(text: str, work_date: date) -> datetime | None:
        text = text.strip()
        if not text or text == "—":
            return None
        for fmt in ("%H:%M", "%H:%M:%S"):
            try:
                parsed = datetime.strptime(text, fmt)
                return datetime.combine(work_date, parsed.time())
            except ValueError:
                continue
        raise ValueError(f"Neispravan format vremena: {text!r} (koristi HH:MM)")

    def worked_minutes(self) -> int | None:
        """Total shift length: kraj smjene − dolazak (break included)."""
        if not self.dolazak or not self.kraj_smjene:
            return None
        total = (self.kraj_smjene - self.dolazak).total_seconds() / 60
        return max(0, int(round(total)))

    @staticmethod
    def format_duration(minutes: int) -> str:
        if minutes < 60:
            return f"{minutes} min"
        hours, mins = divmod(minutes, 60)
        if mins == 0:
            return f"{hours}h"
        return f"{hours}h {mins}m"

    def overtime_minutes(self, expected: int) -> int | None:
        worked = self.worked_minutes()
        if worked is None:
            return None
        return max(0, worked - expected)

    def validation_warnings(self) -> list[str]:
        warnings: list[str] = []
        ordered = [
            ("Dolazak", self.dolazak),
            ("Početak pauze", self.pocetak_pauze),
            ("Kraj pauze", self.kraj_pauze),
            ("Kraj smjene", self.kraj_smjene),
        ]
        filled = [(label, t) for label, t in ordered if t is not None]
        for i in range(len(filled) - 1):
            if filled[i][1] >= filled[i + 1][1]:
                warnings.append(
                    f"{filled[i][0]} ({filled[i][1].strftime('%H:%M')}) mora biti prije "
                    f"{filled[i + 1][0]} ({filled[i + 1][1].strftime('%H:%M')})."
                )
        if self.pocetak_pauze and not self.kraj_pauze:
            warnings.append("Početak pauze je unesen, ali kraj pauze nije.")
        if self.kraj_pauze and not self.pocetak_pauze:
            warnings.append("Kraj pauze je unesen, ali početak pauze nije.")
        return warnings

    def to_export_dict(self, name: str, *, expected: int, raspored: str) -> dict:
        fmt = "%H:%M:%S"
        worked = self.worked_minutes()
        return {
            "ime": name,
            "raspored": raspored,
            "ocekivane_minute": expected,
            "dolazak": self.dolazak.strftime(fmt) if self.dolazak else None,
            "pocetak_pauze": self.pocetak_pauze.strftime(fmt) if self.pocetak_pauze else None,
            "kraj_pauze": self.kraj_pauze.strftime(fmt) if self.kraj_pauze else None,
            "kraj_smjene": self.kraj_smjene.strftime(fmt) if self.kraj_smjene else None,
            "radne_minute": worked,
            "prekovremene_minute": self.overtime_minutes(expected),
        }

    @classmethod
    def from_export_row(cls, row: dict, work_date: date) -> DayRecord:
        record = cls()

        def _parse(key: str) -> datetime | None:
            raw = row.get(key)
            if not raw:
                return None
            for fmt in ("%H:%M:%S", "%H:%M"):
                try:
                    parsed = datetime.strptime(raw, fmt)
                    return datetime.combine(work_date, parsed.time())
                except ValueError:
                    continue
            return None

        record.dolazak = _parse("dolazak")
        record.pocetak_pauze = _parse("pocetak_pauze")
        record.kraj_pauze = _parse("kraj_pauze")
        record.kraj_smjene = _parse("kraj_smjene")
        return record


@dataclass
class Workday:
    work_date: date = field(default_factory=date.today)
    records: dict[str, DayRecord] = field(default_factory=dict)

    def ensure_employees(self, names: list[str]) -> None:
        for name in names:
            self.records.setdefault(name, DayRecord())

    def active_employees(self, names: list[str]) -> list[str]:
        return [n for n in names if self.records[n].has_activity()]

    def all_active_finished(self, names: list[str]) -> bool:
        active = self.active_employees(names)
        if not active:
            return False
        return all(self.records[n].next_step() == ShiftStep.DONE for n in active)

    def archive_payload(self, names: list[str]) -> dict:
        from employees import expected_minutes, schedule_label

        active = self.active_employees(names)
        return {
            "datum": self.work_date.strftime("%d-%m-%Y"),
            "zaposleni": [
                self.records[n].to_export_dict(
                    n,
                    expected=expected_minutes(n),
                    raspored=schedule_label(n),
                )
                for n in active
            ],
            "arhivirano": datetime.now().isoformat(timespec="seconds"),
        }
