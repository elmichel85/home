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
