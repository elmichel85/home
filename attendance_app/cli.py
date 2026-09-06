"""Command-line interface for the attendance app.

Usage examples:

    python -m attendance_app add-employee "Alice"
    python -m attendance_app check-in "Alice"
    python -m attendance_app check-out "Alice"
    python -m attendance_app status
    python -m attendance_app report --start 2026-09-01 --end 2026-09-30
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from typing import List, Optional

from .store import (
    AttendanceError,
    AttendanceStore,
    DEFAULT_DB_PATH,
    Session,
    end_of_day_exclusive_bound,
    to_iso,
    total_hours,
)


def _parse_datetime_arg(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"invalid date/time '{value}', expected YYYY-MM-DD or "
            "YYYY-MM-DDTHH:MM:SS"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="attendance_app",
        description="Track employee check-in/check-out attendance.",
    )
    parser.add_argument(
        "--db",
        default=os.environ.get("ATTENDANCE_DB", DEFAULT_DB_PATH),
        help=f"Path to the SQLite database file "
        f"(default: {DEFAULT_DB_PATH}, or $ATTENDANCE_DB).",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    add = subparsers.add_parser("add-employee", help="Add a new employee.")
    add.add_argument("name")

    remove = subparsers.add_parser("remove-employee", help="Remove an employee and their history.")
    remove.add_argument("name")

    subparsers.add_parser("list-employees", help="List all known employees.")

    check_in = subparsers.add_parser("check-in", help="Check an employee in.")
    check_in.add_argument("name")
    check_in.add_argument(
        "--time",
        type=_parse_datetime_arg,
        help="Check-in time (default: now). E.g. 2026-09-06T09:00:00.",
    )

    check_out = subparsers.add_parser("check-out", help="Check an employee out.")
    check_out.add_argument("name")
    check_out.add_argument(
        "--time",
        type=_parse_datetime_arg,
        help="Check-out time (default: now). E.g. 2026-09-06T17:30:00.",
    )

    status = subparsers.add_parser("status", help="Show who is currently checked in.")
    status.add_argument("--json", action="store_true", help="Print as JSON.")

    report = subparsers.add_parser("report", help="Show attendance sessions and hours worked.")
    report.add_argument("--employee", help="Limit the report to one employee.")
    report.add_argument(
        "--start", type=_parse_datetime_arg, help="Only sessions starting on/after this date/time."
    )
    report.add_argument(
        "--end", type=_parse_datetime_arg, help="Only sessions starting on/before this date/time."
    )
    report.add_argument("--json", action="store_true", help="Print as JSON.")

    return parser


def _print_status(sessions: List[Session]) -> None:
    if not sessions:
        print("No one is currently checked in.")
        return
    print("Currently checked in:")
    for s in sessions:
        print(f"  {s.employee:<20} since {s.check_in}  ({s.duration_hours():.2f}h so far)")


def _print_report(sessions: List[Session]) -> None:
    if not sessions:
        print("No sessions found.")
        return

    by_employee: dict = {}
    for s in sessions:
        by_employee.setdefault(s.employee, []).append(s)

    for employee, employee_sessions in sorted(by_employee.items()):
        print(f"{employee}:")
        for s in employee_sessions:
            check_out = s.check_out or "(still checked in)"
            print(f"    {s.check_in} -> {check_out}   {s.duration_hours():.2f}h")
        print(f"    total: {total_hours(employee_sessions):.2f}h")
        print()

    print(f"Grand total: {total_hours(sessions):.2f}h across {len(sessions)} session(s)")


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    store = AttendanceStore(args.db)
    try:
        if args.command == "add-employee":
            store.add_employee(args.name)
            print(f"Added employee '{args.name}'.")

        elif args.command == "remove-employee":
            store.remove_employee(args.name)
            print(f"Removed employee '{args.name}'.")

        elif args.command == "list-employees":
            employees = store.list_employees()
            if not employees:
                print("No employees yet.")
            for name in employees:
                print(name)

        elif args.command == "check-in":
            when = to_iso(args.time) if args.time else None
            session = store.check_in(args.name, when)
            print(f"Checked in '{args.name}' at {session.check_in}.")

        elif args.command == "check-out":
            when = to_iso(args.time) if args.time else None
            session = store.check_out(args.name, when)
            print(
                f"Checked out '{args.name}' at {session.check_out} "
                f"({session.duration_hours():.2f}h worked)."
            )

        elif args.command == "status":
            sessions = store.currently_checked_in()
            if args.json:
                print(json.dumps([s.as_dict() for s in sessions], indent=2))
            else:
                _print_status(sessions)

        elif args.command == "report":
            start_iso = to_iso(args.start) if args.start else None
            end_iso = None
            if args.end:
                end_iso = to_iso(
                    end_of_day_exclusive_bound(_is_date_only(args.end), args.end)
                )
            sessions = store.sessions_for(args.employee, start_iso, end_iso)
            if args.json:
                print(json.dumps([s.as_dict() for s in sessions], indent=2))
            else:
                _print_report(sessions)

        return 0
    except AttendanceError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        store.close()


def _is_date_only(dt: datetime) -> bool:
    return dt.hour == dt.minute == dt.second == dt.microsecond == 0


if __name__ == "__main__":
    sys.exit(main())
