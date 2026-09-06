import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta

from attendance_app import cli
from attendance_app.store import (
    AttendanceError,
    AttendanceStore,
    end_of_day_exclusive_bound,
    now_iso,
    to_iso,
    total_hours,
)


class AttendanceStoreTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(self.db_path)  # let AttendanceStore create it fresh
        self.store = AttendanceStore(self.db_path)

    def tearDown(self):
        self.store.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_add_and_list_employees(self):
        self.store.add_employee("Alice")
        self.store.add_employee("Bob")
        self.assertEqual(self.store.list_employees(), ["Alice", "Bob"])

    def test_add_duplicate_employee_raises(self):
        self.store.add_employee("Alice")
        with self.assertRaises(AttendanceError):
            self.store.add_employee("Alice")

    def test_add_empty_name_raises(self):
        with self.assertRaises(AttendanceError):
            self.store.add_employee("   ")

    def test_remove_employee_clears_sessions(self):
        self.store.add_employee("Alice")
        self.store.check_in("Alice", "2026-09-06T09:00:00")
        self.store.remove_employee("Alice")
        self.assertEqual(self.store.list_employees(), [])
        with self.assertRaises(AttendanceError):
            self.store.check_in("Alice")

    def test_check_in_unknown_employee_raises(self):
        with self.assertRaises(AttendanceError):
            self.store.check_in("Ghost")

    def test_check_in_and_check_out(self):
        self.store.add_employee("Alice")
        session = self.store.check_in("Alice", "2026-09-06T09:00:00")
        self.assertTrue(session.is_open)

        done = self.store.check_out("Alice", "2026-09-06T17:00:00")
        self.assertFalse(done.is_open)
        self.assertAlmostEqual(done.duration_hours(), 8.0)

    def test_double_check_in_raises(self):
        self.store.add_employee("Alice")
        self.store.check_in("Alice", "2026-09-06T09:00:00")
        with self.assertRaises(AttendanceError):
            self.store.check_in("Alice", "2026-09-06T10:00:00")

    def test_check_out_without_check_in_raises(self):
        self.store.add_employee("Alice")
        with self.assertRaises(AttendanceError):
            self.store.check_out("Alice")

    def test_check_out_before_check_in_raises(self):
        self.store.add_employee("Alice")
        self.store.check_in("Alice", "2026-09-06T09:00:00")
        with self.assertRaises(AttendanceError):
            self.store.check_out("Alice", "2026-09-06T08:00:00")

    def test_currently_checked_in(self):
        self.store.add_employee("Alice")
        self.store.add_employee("Bob")
        self.store.check_in("Alice", "2026-09-06T09:00:00")
        self.store.check_in("Bob", "2026-09-06T09:15:00")
        self.store.check_out("Bob", "2026-09-06T10:00:00")

        open_sessions = self.store.currently_checked_in()
        self.assertEqual([s.employee for s in open_sessions], ["Alice"])

    def test_sessions_for_filters_by_employee_and_range(self):
        self.store.add_employee("Alice")
        self.store.add_employee("Bob")
        self.store.check_in("Alice", "2026-09-01T09:00:00")
        self.store.check_out("Alice", "2026-09-01T17:00:00")
        self.store.check_in("Alice", "2026-09-08T09:00:00")
        self.store.check_out("Alice", "2026-09-08T17:00:00")
        self.store.check_in("Bob", "2026-09-01T09:00:00")
        self.store.check_out("Bob", "2026-09-01T17:00:00")

        alice_only = self.store.sessions_for(employee="Alice")
        self.assertEqual(len(alice_only), 2)

        first_week = self.store.sessions_for(
            employee="Alice", start="2026-09-01T00:00:00", end="2026-09-02T00:00:00"
        )
        self.assertEqual(len(first_week), 1)
        self.assertEqual(first_week[0].check_in, "2026-09-01T09:00:00")

    def test_total_hours(self):
        self.store.add_employee("Alice")
        self.store.check_in("Alice", "2026-09-01T09:00:00")
        self.store.check_out("Alice", "2026-09-01T13:00:00")
        self.store.check_in("Alice", "2026-09-02T09:00:00")
        self.store.check_out("Alice", "2026-09-02T12:30:00")

        sessions = self.store.sessions_for(employee="Alice")
        self.assertAlmostEqual(total_hours(sessions), 7.5)

    def test_open_session_duration_uses_now(self):
        self.store.add_employee("Alice")
        self.store.check_in("Alice", "2026-09-06T09:00:00")
        session = self.store.currently_checked_in()[0]
        later = "2026-09-06T11:30:00"
        self.assertAlmostEqual(session.duration_hours(later), 2.5)


class EndOfDayBoundTests(unittest.TestCase):
    def test_bare_date_extends_to_next_day(self):
        dt = datetime(2026, 9, 6)
        bumped = end_of_day_exclusive_bound(True, dt)
        self.assertEqual(bumped, dt + timedelta(days=1))

    def test_full_timestamp_is_unchanged(self):
        dt = datetime(2026, 9, 6, 14, 30)
        self.assertEqual(end_of_day_exclusive_bound(False, dt), dt)


class TimeHelpersTests(unittest.TestCase):
    def test_now_iso_is_isoformat_parseable(self):
        value = now_iso()
        self.assertEqual(datetime.fromisoformat(value).isoformat(), value)

    def test_to_iso_drops_microseconds(self):
        dt = datetime(2026, 9, 6, 9, 0, 0, 123456)
        self.assertEqual(to_iso(dt), "2026-09-06T09:00:00")


class CliTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def _run(self, *args):
        return cli.main(["--db", self.db_path, *args])

    def test_full_workflow(self):
        self.assertEqual(self._run("add-employee", "Alice"), 0)
        self.assertEqual(self._run("check-in", "Alice", "--time", "2026-09-06T09:00:00"), 0)
        self.assertEqual(self._run("check-out", "Alice", "--time", "2026-09-06T17:00:00"), 0)

        with AttendanceStore(self.db_path) as store:
            sessions = store.sessions_for(employee="Alice")
            self.assertEqual(len(sessions), 1)
            self.assertAlmostEqual(sessions[0].duration_hours(), 8.0)

    def test_check_in_unknown_employee_returns_error_code(self):
        self.assertEqual(self._run("check-in", "Ghost"), 1)

    def test_status_json_output(self, capsys=None):
        self._run("add-employee", "Alice")
        self._run("check-in", "Alice", "--time", "2026-09-06T09:00:00")

        import io
        import contextlib

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self._run("status", "--json")
        payload = json.loads(buf.getvalue())
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["employee"], "Alice")


if __name__ == "__main__":
    unittest.main()
