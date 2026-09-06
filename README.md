# network-access-checker

A small, dependency-free command-line tool for checking what network
access a machine (or container) currently has: DNS resolution, TCP
reachability to specific hosts/ports, ICMP ping, local interface
addresses, and an overall "do I have internet?" verdict.

Only the Python standard library is used, so there's nothing to
install beyond Python 3.7+.

## Usage

Run the default checks (a handful of well-known internet hosts on
port 443, DNS resolution, and ICMP ping):

```bash
python -m network_access_checker
```

Check specific hosts/ports (e.g. an internal service), in addition to
the defaults:

```bash
python -m network_access_checker --target internal-db:5432 --target 10.0.0.5:22
```

Check *only* your own targets, skipping the default internet checks:

```bash
python -m network_access_checker --only-targets --target internal-api:8080
```

Skip ICMP ping (useful in environments where ICMP is blocked/slow, e.g.
most containers) and get machine-readable output:

```bash
python -m network_access_checker --no-ping --json
```

The process exits with status `0` if internet access was detected and
`1` otherwise, so it can be used directly in scripts or health checks.

## Example output

```
Host: my-container
Local addresses: 172.17.0.2

DNS resolution:
  [OK  ] github.com -> 140.82.112.3
  [OK  ] google.com -> 142.250.premium.ip

TCP reachability:
  [OK  ] tcp 1.1.1.1:443 — 8.2 ms
  [OK  ] tcp 8.8.8.8:443 — 11.4 ms
  [OK  ] tcp github.com:443 — 24.1 ms

ICMP ping:
  [FAIL] ping 1.1.1.1 — no reply (ICMP may be blocked)

Internet access: YES
```

## Using it as a library

```python
from network_access_checker import run_report, check_tcp_port

report = run_report()
print(report.internet_reachable)

result = check_tcp_port("example.com", 443)
print(result.reachable, result.latency_ms)
```

## Running tests

```bash
python -m unittest discover -s tests
```

# attendance-app

A small, dependency-free command-line tool for tracking employee
attendance: add employees, check them in and out, see who's currently
checked in, and run reports on hours worked. Data is stored in a local
SQLite database (Python's built-in `sqlite3`), so nothing beyond
Python 3.7+ is required.

## Usage

Add employees, then check them in and out:

```bash
python -m attendance_app add-employee "Alice"
python -m attendance_app check-in "Alice"
python -m attendance_app check-out "Alice"
```

By default, times default to *now*, but you can supply an explicit
ISO-8601 date/time:

```bash
python -m attendance_app check-in "Alice" --time 2026-09-06T09:00:00
python -m attendance_app check-out "Alice" --time 2026-09-06T17:00:00
```

See who's currently checked in:

```bash
python -m attendance_app status
```

Run a report of sessions and hours worked, optionally filtered by
employee and/or date range:

```bash
python -m attendance_app report
python -m attendance_app report --employee "Alice" --start 2026-09-01 --end 2026-09-30
python -m attendance_app report --json
```

List or remove employees:

```bash
python -m attendance_app list-employees
python -m attendance_app remove-employee "Alice"
```

By default, data is stored in `attendance.db` in the current
directory. Point at a different file with `--db path/to/file.db` or the
`ATTENDANCE_DB` environment variable.

The process exits with status `0` on success and `1` on error (e.g.
double check-in, unknown employee), so it can be used directly in
scripts.

## Using it as a library

```python
from attendance_app import AttendanceStore

with AttendanceStore("attendance.db") as store:
    store.add_employee("Alice")
    store.check_in("Alice")
    store.check_out("Alice")
    print(store.sessions_for(employee="Alice"))
```

## Running tests

```bash
python -m unittest discover -s tests
```
