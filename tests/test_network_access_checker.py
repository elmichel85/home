import socket
import unittest
from unittest.mock import patch

from network_access_checker.checker import (
    TargetResult,
    check_dns,
    check_internet,
    check_tcp_port,
    run_report,
)


class TargetResultTests(unittest.TestCase):
    def test_as_dict_roundtrip(self):
        result = TargetResult("example.com", 443, True, 12.3, None)
        self.assertEqual(
            result.as_dict(),
            {
                "host": "example.com",
                "port": 443,
                "reachable": True,
                "latency_ms": 12.3,
                "error": None,
            },
        )


class CheckDnsTests(unittest.TestCase):
    def test_resolves_known_ip_literal(self):
        # An IP literal always "resolves" to itself.
        self.assertEqual(check_dns("127.0.0.1"), "127.0.0.1")

    def test_returns_none_on_failure(self):
        with patch("socket.gethostbyname", side_effect=socket.gaierror):
            self.assertIsNone(check_dns("does-not-exist.invalid"))


class CheckTcpPortTests(unittest.TestCase):
    def test_reachable_against_local_listener(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        host, port = server.getsockname()
        try:
            result = check_tcp_port(host, port, timeout=1)
            self.assertTrue(result.reachable)
            self.assertIsNone(result.error)
            self.assertIsNotNone(result.latency_ms)
        finally:
            server.close()

    def test_unreachable_port_reports_failure(self):
        # Port 0 connect attempts fail immediately/predictably.
        result = check_tcp_port("127.0.0.1", 1, timeout=0.5)
        self.assertFalse(result.reachable)
        self.assertIsNotNone(result.error)


class CheckInternetTests(unittest.TestCase):
    def test_true_when_any_target_reachable(self):
        with patch(
            "network_access_checker.checker.check_tcp_port",
            side_effect=[
                TargetResult("a", 443, False, None, "no"),
                TargetResult("b", 443, True, 5.0, None),
            ],
        ):
            self.assertTrue(check_internet([("a", 443), ("b", 443)]))

    def test_false_when_all_unreachable(self):
        with patch(
            "network_access_checker.checker.check_tcp_port",
            return_value=TargetResult("a", 443, False, None, "no"),
        ):
            self.assertFalse(check_internet([("a", 443)]))


class RunReportTests(unittest.TestCase):
    def test_report_shape(self):
        with patch(
            "network_access_checker.checker.check_tcp_port",
            return_value=TargetResult("a", 443, True, 1.0, None),
        ), patch(
            "network_access_checker.checker.check_ping",
            return_value=TargetResult("a", 0, True, 1.0, None),
        ):
            report = run_report(tcp_targets=[("a", 443)])
            self.assertTrue(report.internet_reachable)
            self.assertEqual(len(report.tcp_results), 1)
            self.assertIn("hostname", report.as_dict())


if __name__ == "__main__":
    unittest.main()
