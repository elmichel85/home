"""SQLite-backed storage for employee check-in/check-out attendance.

Everything here uses only the Python standard library (sqlite3), so
the app runs anywhere Python 3.7+ runs with no extra installs.

Timestamps are stored as naive ISO-8601 strings (``YYYY-MM-DDTHH:MM:SS``)
in whatever local time the caller supplies, so they sort and compare
lexicographically the same way they compare chronologically.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Union

DEFAULT_DB_PATH = "attendance.db"


class AttendanceError(Exception):
    """Raised for invalid attendance operations (bad employee, double
    check-in, checking out without checking in, etc.)."""


def now_iso() -> str:
    """The current local time as a seconds-precision ISO-8601 string."""
    return datetime.now().replace(microsecond=0).isoformat()


def to_iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


@dataclass
class Session:
    """One check-in/check-out record for an employee."""

    id: int
    employee: str
    check_in: str
    check_out: Optional[str]

    @property
    def is_open(self) -> bool:
        return self.check_out is None

    def duration_hours(self, now: Optional[str] = None) -> float:
        """Hours worked in this session.

        For an open session (no check-out yet), duration is measured up
        to ``now`` (an ISO string), defaulting to the current time.
        """
        start = datetime.fromisoformat(self.check_in)
        end = datetime.fromisoformat(self.check_out or now or now_iso())
        return (end - start).total_seconds() / 3600

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "employee": self.employee,
            "check_in": self.check_in,
            "check_out": self.check_out,
            "duration_hours": round(self.duration_hours(), 2),
        }


class AttendanceStore:
    """Manages employees and their check-in/check-out sessions."""

    def __init__(self, db_path: Union[str, Path] = DEFAULT_DB_PATH):
        self.db_path = str(db_path)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._init_schema()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "AttendanceStore":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL REFERENCES employees(id),
                check_in TEXT NOT NULL,
                check_out TEXT
            );
            """
        )
        self._conn.commit()

    # -- employees ---------------------------------------------------

    def add_employee(self, name: str) -> None:
        name = name.strip()
        if not name:
            raise AttendanceError("employee name must not be empty")
        try:
            self._conn.execute("INSERT INTO employees (name) VALUES (?)", (name,))
            self._conn.commit()
        except sqlite3.IntegrityError:
            raise AttendanceError(f"employee '{name}' already exists")

    def remove_employee(self, name: str) -> None:
        row = self._get_employee_row(name)
        self._conn.execute("DELETE FROM sessions WHERE employee_id = ?", (row["id"],))
        self._conn.execute("DELETE FROM employees WHERE id = ?", (row["id"],))
        self._conn.commit()

    def list_employees(self) -> List[str]:
        rows = self._conn.execute("SELECT name FROM employees ORDER BY name").fetchall()
        return [r["name"] for r in rows]

    def _get_employee_row(self, name: str) -> sqlite3.Row:
        row = self._conn.execute(
            "SELECT * FROM employees WHERE name = ?", (name,)
        ).fetchone()
        if row is None:
            raise AttendanceError(f"unknown employee '{name}'")
        return row

    # -- check-in / check-out -----------------------------------------

    def _open_session_row(self, employee_id: int) -> Optional[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM sessions WHERE employee_id = ? AND check_out IS NULL",
            (employee_id,),
        ).fetchone()

    def check_in(self, name: str, when: Optional[str] = None) -> Session:
        employee = self._get_employee_row(name)
        if self._open_session_row(employee["id"]) is not None:
            raise AttendanceError(f"'{name}' is already checked in")
        when = when or now_iso()
        cur = self._conn.execute(
            "INSERT INTO sessions (employee_id, check_in) VALUES (?, ?)",
            (employee["id"], when),
        )
        self._conn.commit()
        return Session(cur.lastrowid, name, when, None)

    def check_out(self, name: str, when: Optional[str] = None) -> Session:
        employee = self._get_employee_row(name)
        open_row = self._open_session_row(employee["id"])
        if open_row is None:
            raise AttendanceError(f"'{name}' is not checked in")
        when = when or now_iso()
        if when < open_row["check_in"]:
            raise AttendanceError("check-out time cannot be before check-in time")
        self._conn.execute(
            "UPDATE sessions SET check_out = ? WHERE id = ?", (when, open_row["id"])
        )
        self._conn.commit()
        return Session(open_row["id"], name, open_row["check_in"], when)

    def currently_checked_in(self) -> List[Session]:
        rows = self._conn.execute(
            """
            SELECT sessions.id AS id, employees.name AS name,
                   sessions.check_in AS check_in, sessions.check_out AS check_out
            FROM sessions
            JOIN employees ON employees.id = sessions.employee_id
            WHERE sessions.check_out IS NULL
            ORDER BY sessions.check_in
            """
        ).fetchall()
        return [Session(r["id"], r["name"], r["check_in"], r["check_out"]) for r in rows]

    # -- reporting -----------------------------------------------------

    def sessions_for(
        self,
        employee: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> List[Session]:
        """All sessions matching the given filters, oldest first.

        ``start`` is an inclusive lower bound and ``end`` an exclusive
        upper bound on the check-in time, both ISO strings.
        """
        query = """
            SELECT sessions.id AS id, employees.name AS name,
                   sessions.check_in AS check_in, sessions.check_out AS check_out
            FROM sessions
            JOIN employees ON employees.id = sessions.employee_id
            WHERE 1 = 1
        """
        params: list = []
        if employee:
            query += " AND employees.name = ?"
            params.append(employee)
        if start:
            query += " AND sessions.check_in >= ?"
            params.append(start)
        if end:
            query += " AND sessions.check_in < ?"
            params.append(end)
        query += " ORDER BY sessions.check_in"
        rows = self._conn.execute(query, params).fetchall()
        return [Session(r["id"], r["name"], r["check_in"], r["check_out"]) for r in rows]


def total_hours(sessions: List[Session]) -> float:
    """Sum of the durations of the given sessions, in hours."""
    return sum(s.duration_hours() for s in sessions)


def end_of_day_exclusive_bound(date_only: bool, dt: datetime) -> datetime:
    """Shift a bare-date ``--end`` argument to the start of the next day.

    So ``--end 2026-09-06`` includes the whole day of the 6th, rather
    than excluding it entirely (since sessions_for's ``end`` is an
    exclusive bound).
    """
    if date_only:
        return dt + timedelta(days=1)
    return dt
