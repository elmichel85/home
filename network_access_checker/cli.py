"""Command-line interface for the network access checker.

Usage examples:

    python -m network_access_checker
    python -m network_access_checker --target example.com:443 --target 10.0.0.5:22
    python -m network_access_checker --no-ping --json
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Tuple

from .checker import TargetResult, run_report


def _parse_target(value: str) -> Tuple[str, int]:
    if ":" not in value:
        raise argparse.ArgumentTypeError(
            f"target '{value}' must be in host:port form, e.g. example.com:443"
        )
    host, _, port_str = value.rpartition(":")
    if not host:
        raise argparse.ArgumentTypeError(f"target '{value}' is missing a host")
    try:
        port = int(port_str)
    except ValueError:
        raise argparse.ArgumentTypeError(f"target '{value}' has a non-numeric port")
    return host, port


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="network_access_checker",
        description="Check what network access this machine currently has.",
    )
    parser.add_argument(
        "--target",
        "-t",
        dest="targets",
        action="append",
        type=_parse_target,
        metavar="HOST:PORT",
        help="Extra host:port to test (repeatable). Adds to the default "
        "internet reachability targets unless --only-targets is set.",
    )
    parser.add_argument(
        "--only-targets",
        action="store_true",
        help="Test only the --target hosts given, skipping the default set.",
    )
    parser.add_argument(
        "--no-ping",
        action="store_true",
        help="Skip ICMP ping checks (useful where ICMP is blocked/slow).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the report as JSON instead of a human-readable summary.",
    )
    return parser


def _format_target_line(result: TargetResult, label: str) -> str:
    status = "OK" if result.reachable else "FAIL"
    detail = f"{result.latency_ms} ms" if result.reachable else (result.error or "unreachable")
    port_part = f":{result.port}" if result.port else ""
    return f"  [{status:4}] {label} {result.host}{port_part} — {detail}"


def print_human_report(report) -> None:
    print(f"Host: {report.hostname}")
    print(f"Local addresses: {', '.join(report.local_addresses)}")
    print()

    print("DNS resolution:")
    for host, ip in report.dns_results.items():
        status = "OK" if ip else "FAIL"
        print(f"  [{status:4}] {host} -> {ip or 'could not resolve'}")
    print()

    print("TCP reachability:")
    for result in report.tcp_results:
        print(_format_target_line(result, "tcp"))
    print()

    if report.ping_results:
        print("ICMP ping:")
        for result in report.ping_results:
            print(_format_target_line(result, "ping"))
        print()

    overall = "YES" if report.internet_reachable else "NO"
    print(f"Internet access: {overall}")


def main(argv: List[str] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    tcp_targets = None
    if args.only_targets:
        if not args.targets:
            parser.error("--only-targets requires at least one --target")
        tcp_targets = args.targets
    elif args.targets:
        from .checker import DEFAULT_INTERNET_TARGETS

        tcp_targets = list(DEFAULT_INTERNET_TARGETS) + args.targets

    report = run_report(tcp_targets=tcp_targets, do_ping=not args.no_ping)

    if args.json:
        print(json.dumps(report.as_dict(), indent=2))
    else:
        print_human_report(report)

    return 0 if report.internet_reachable else 1


if __name__ == "__main__":
    sys.exit(main())
