"""Network Access Checker.

A small, dependency-free toolkit for checking what network access a
machine or container currently has: DNS resolution, TCP reachability
to specific hosts/ports, ICMP ping, local interface addresses, and a
quick "do I have internet at all" summary.
"""

from .checker import (
    NetworkReport,
    TargetResult,
    check_dns,
    check_internet,
    check_ping,
    check_tcp_port,
    list_local_interfaces,
    run_report,
)

__all__ = [
    "NetworkReport",
    "TargetResult",
    "check_dns",
    "check_internet",
    "check_ping",
    "check_tcp_port",
    "list_local_interfaces",
    "run_report",
]
