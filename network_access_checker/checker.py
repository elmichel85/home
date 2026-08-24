"""Core network-access checks.

Everything here uses only the Python standard library, so the tool
runs anywhere Python 3.7+ runs with no extra installs.
"""

from __future__ import annotations

import platform
import socket
import subprocess
import time
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

# A small set of well-known, highly-available endpoints used to answer
# "do I have internet access at all?" without depending on any single
# provider. All are checked on 443 (HTTPS) since that's the port most
# commonly left open through firewalls/proxies.
DEFAULT_INTERNET_TARGETS: Tuple[Tuple[str, int], ...] = (
    ("1.1.1.1", 443),      # Cloudflare
    ("8.8.8.8", 443),      # Google DNS
    ("github.com", 443),
)

DEFAULT_DNS_HOSTNAMES: Tuple[str, ...] = ("github.com", "google.com")


@dataclass
class TargetResult:
    """Result of a single reachability check against one host:port."""

    host: str
    port: int
    reachable: bool
    latency_ms: Optional[float] = None
    error: Optional[str] = None

    def as_dict(self) -> dict:
        return {
            "host": self.host,
            "port": self.port,
            "reachable": self.reachable,
            "latency_ms": self.latency_ms,
            "error": self.error,
        }


@dataclass
class NetworkReport:
    """Aggregate result of a full network-access check run."""

    hostname: str
    local_addresses: List[str]
    dns_results: dict = field(default_factory=dict)  # hostname -> ip or None
    tcp_results: List[TargetResult] = field(default_factory=list)
    ping_results: List[TargetResult] = field(default_factory=list)
    internet_reachable: bool = False

    def as_dict(self) -> dict:
        return {
            "hostname": self.hostname,
            "local_addresses": self.local_addresses,
            "dns_results": self.dns_results,
            "tcp_results": [t.as_dict() for t in self.tcp_results],
            "ping_results": [t.as_dict() for t in self.ping_results],
            "internet_reachable": self.internet_reachable,
        }


def list_local_interfaces() -> List[str]:
    """Return local IP addresses this machine is known by.

    Uses only stdlib socket calls, so it works without a network
    interfaces library. Not exhaustive for multi-homed hosts, but
    reliably reports at least the primary address(es).
    """
    addresses = set()

    hostname = socket.gethostname()
    try:
        for info in socket.getaddrinfo(hostname, None):
            addr = info[4][0]
            if addr:
                addresses.add(addr)
    except socket.gaierror:
        pass

    # This doesn't actually send any packets (UDP connect just picks a
    # local route), but it reliably reveals the outbound-facing address.
    for family, target in ((socket.AF_INET, ("8.8.8.8", 80)),):
        try:
            with socket.socket(family, socket.SOCK_DGRAM) as s:
                s.connect(target)
                addresses.add(s.getsockname()[0])
        except OSError:
            pass

    addresses.discard("127.0.0.1")
    addresses.discard("::1")
    return sorted(addresses) or ["127.0.0.1"]


def check_dns(hostname: str) -> Optional[str]:
    """Resolve a hostname. Returns the IP address, or None if it fails."""
    try:
        return socket.gethostbyname(hostname)
    except socket.gaierror:
        return None


def check_tcp_port(host: str, port: int, timeout: float = 3.0) -> TargetResult:
    """Attempt a TCP connect to host:port and time how long it takes."""
    start = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            elapsed_ms = (time.monotonic() - start) * 1000
            return TargetResult(host, port, True, round(elapsed_ms, 1))
    except (socket.timeout, OSError) as exc:
        return TargetResult(host, port, False, None, str(exc))


def check_ping(host: str, timeout: float = 3.0) -> TargetResult:
    """Send a single ICMP echo request via the OS `ping` command.

    Falls back gracefully (reachable=False, error set) if `ping` is
    unavailable or ICMP is blocked, which is common in containers.
    """
    count_flag = "-n" if platform.system().lower() == "windows" else "-c"
    timeout_flag = "-w" if platform.system().lower() == "windows" else "-W"
    timeout_value = str(int(timeout * 1000)) if platform.system().lower() == "windows" else str(int(timeout))
    cmd = ["ping", count_flag, "1", timeout_flag, timeout_value, host]

    start = time.monotonic()
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout + 2,
        )
        elapsed_ms = (time.monotonic() - start) * 1000
        if result.returncode == 0:
            return TargetResult(host, 0, True, round(elapsed_ms, 1))
        return TargetResult(host, 0, False, None, "no reply (ICMP may be blocked)")
    except FileNotFoundError:
        return TargetResult(host, 0, False, None, "ping command not found")
    except subprocess.TimeoutExpired:
        return TargetResult(host, 0, False, None, "timed out")


def check_internet(targets: Sequence[Tuple[str, int]] = DEFAULT_INTERNET_TARGETS) -> bool:
    """Return True if at least one well-known internet host is reachable."""
    return any(check_tcp_port(host, port).reachable for host, port in targets)


def run_report(
    tcp_targets: Optional[Sequence[Tuple[str, int]]] = None,
    dns_hostnames: Sequence[str] = DEFAULT_DNS_HOSTNAMES,
    do_ping: bool = True,
) -> NetworkReport:
    """Run the full suite of checks and return a NetworkReport."""
    hostname = socket.gethostname()
    local_addresses = list_local_interfaces()

    dns_results = {h: check_dns(h) for h in dns_hostnames}

    tcp_targets = tcp_targets if tcp_targets is not None else DEFAULT_INTERNET_TARGETS
    tcp_results = [check_tcp_port(host, port) for host, port in tcp_targets]

    ping_results: List[TargetResult] = []
    if do_ping:
        ping_hosts = {host for host, _ in tcp_targets}
        ping_results = [check_ping(host) for host in ping_hosts]

    internet_reachable = any(r.reachable for r in tcp_results)

    return NetworkReport(
        hostname=hostname,
        local_addresses=local_addresses,
        dns_results=dns_results,
        tcp_results=tcp_results,
        ping_results=ping_results,
        internet_reachable=internet_reachable,
    )
