"""Attendance App.

A small, dependency-free CLI for tracking employee attendance via
check-in/check-out events, backed by a local SQLite database.
"""

from .store import (
    AttendanceError,
    AttendanceStore,
    Session,
    now_iso,
    to_iso,
    total_hours,
)

__all__ = [
    "AttendanceError",
    "AttendanceStore",
    "Session",
    "now_iso",
    "to_iso",
    "total_hours",
]
