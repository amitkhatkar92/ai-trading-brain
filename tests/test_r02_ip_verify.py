"""
tests/test_r02_ip_verify.py
Unit tests for R-02 Dhan static IP verification logic.
Tests cover verify_ip() only — no network calls, no broker state changes.
"""
from __future__ import annotations

import sys
import types
import unittest

# Stub out network-touching imports so the test runs offline.
_stub_dotenv = types.ModuleType("dotenv")
_stub_dotenv.load_dotenv = lambda *a, **k: None  # type: ignore[attr-defined]
sys.modules.setdefault("dotenv", _stub_dotenv)

from scripts.dhan_auth.dhan_ip_verify import verify_ip  # noqa: E402

_EXPECTED = "178.18.252.24"


class TestVerifyIpGreen(unittest.TestCase):
    """primaryIP or secondaryIP matches expected VPS IP → GREEN."""

    def test_exact_match_primary(self):
        r = verify_ip({"primaryIP": "178.18.252.24"}, _EXPECTED)
        self.assertEqual(r["verdict"], "GREEN")
        self.assertTrue(r["match"])
        self.assertEqual(r["primary_ip"], _EXPECTED)
        self.assertEqual(r["match_type"], "PRIMARY")

    def test_exact_match_secondary(self):
        """Actual observed case: VPS IP is SECONDARY, home IP is PRIMARY."""
        r = verify_ip({"primaryIP": "112.133.194.141", "secondaryIP": "178.18.252.24"}, _EXPECTED)
        self.assertEqual(r["verdict"], "GREEN")
        self.assertTrue(r["match"])
        self.assertEqual(r["match_type"], "SECONDARY")
        self.assertEqual(r["primary_ip"], "112.133.194.141")

    def test_sdk_wrapper_secondary_match(self):
        """Live shape returned on 2026-08-24: VPS IP as secondaryIP."""
        sdk_resp = {
            "status": "success",
            "remarks": "",
            "data": {
                "primaryIP": "112.133.194.141",
                "secondaryIP": "178.18.252.24",
                "modifyDatePrimary": "2026-08-30",
                "modifyDateSecondary": "2026-08-30",
            },
        }
        r = verify_ip(sdk_resp, _EXPECTED)
        self.assertEqual(r["verdict"], "GREEN")
        self.assertEqual(r["match_type"], "SECONDARY")
        self.assertEqual(r["secondary_ip"], _EXPECTED)
        self.assertEqual(r["modify_date_secondary"], "2026-08-30")

    def test_exact_match_with_dates(self):
        r = verify_ip({
            "primaryIP": "178.18.252.24",
            "secondaryIP": "10.0.0.1",
            "modifyDatePrimary": "2026-08-01",
            "modifyDateSecondary": "2026-07-15",
        }, _EXPECTED)
        self.assertEqual(r["verdict"], "GREEN")
        self.assertEqual(r["secondary_ip"], "10.0.0.1")
        self.assertEqual(r["modify_date_primary"], "2026-08-01")
        self.assertEqual(r["modify_date_secondary"], "2026-07-15")

    def test_sdk_wrapper_primary_match(self):
        sdk_resp = {"status": "success", "remarks": "", "data": {"primaryIP": "178.18.252.24"}}
        r = verify_ip(sdk_resp, _EXPECTED)
        self.assertEqual(r["verdict"], "GREEN")
        self.assertEqual(r["match_type"], "PRIMARY")

    def test_whitespace_stripped(self):
        r = verify_ip({"primaryIP": "  178.18.252.24  "}, _EXPECTED)
        self.assertEqual(r["verdict"], "GREEN")


class TestVerifyIpRed(unittest.TestCase):
    """Any non-matching case → RED."""

    def test_wrong_primary_ip(self):
        r = verify_ip({"primaryIP": "1.2.3.4"}, _EXPECTED)
        self.assertEqual(r["verdict"], "RED")
        self.assertFalse(r["match"])
        self.assertIn("1.2.3.4", r["reason"])

    def test_empty_both_ips(self):
        r = verify_ip({"primaryIP": "", "secondaryIP": ""}, _EXPECTED)
        self.assertEqual(r["verdict"], "RED")
        self.assertIsNone(r["primary_ip"])

    def test_secondary_wrong_ip(self):
        """Both IPs present but neither matches."""
        r = verify_ip({"primaryIP": "1.2.3.4", "secondaryIP": "5.6.7.8"}, _EXPECTED)
        self.assertEqual(r["verdict"], "RED")
        self.assertFalse(r["match"])

    def test_none_primary_ip(self):
        r = verify_ip({"primaryIP": None}, _EXPECTED)
        self.assertEqual(r["verdict"], "RED")

    def test_empty_response(self):
        r = verify_ip({}, _EXPECTED)
        self.assertEqual(r["verdict"], "RED")

    # --- Dhan error body patterns (HTTP 200 with error payload) ---

    def test_sdk_wrapper_with_dhan_error_list(self):
        """
        Actual observed Dhan response for accounts without IP whitelist configured:
        SDK wraps it as: {status: 'success', data: [{status: 'ERROR', message: ...}]}
        """
        sdk_resp = {
            "status": "success",
            "remarks": "",
            "data": [{"message": "Something went wrong", "status": "ERROR"}],
        }
        r = verify_ip(sdk_resp, _EXPECTED)
        self.assertEqual(r["verdict"], "RED")
        self.assertIsNone(r["primary_ip"])
        self.assertEqual(r["api_status"], "ERROR")
        self.assertIn("Something went wrong", r["reason"])

    def test_dhan_error_dict_direct(self):
        """Direct REST call returns list with one error dict."""
        # Raw response from Dhan: [{"message": "Something went wrong", "status": "ERROR"}]
        # Our verify_ip receives it as a list; unwrap to dict branch
        direct_resp = [{"message": "Something went wrong", "status": "ERROR"}]
        r = verify_ip(direct_resp, _EXPECTED)
        self.assertEqual(r["verdict"], "RED")
        self.assertEqual(r["api_status"], "ERROR")

    def test_nested_wrong_ip(self):
        r = verify_ip({"status": "success", "data": {"primaryIP": "9.9.9.9"}}, _EXPECTED)
        self.assertEqual(r["verdict"], "RED")

    def test_result_always_has_expected_ip(self):
        r = verify_ip({}, "10.20.30.40")
        self.assertEqual(r["expected_ip"], "10.20.30.40")


class TestVerifyIpResultShape(unittest.TestCase):
    """verify_ip always returns all required keys regardless of input."""

    _REQUIRED = {
        "verdict", "primary_ip", "secondary_ip",
        "modify_date_primary", "modify_date_secondary",
        "expected_ip", "match", "match_type", "reason", "api_status",
    }

    def test_green_has_all_keys(self):
        r = verify_ip({"primaryIP": _EXPECTED}, _EXPECTED)
        self.assertTrue(self._REQUIRED.issubset(r.keys()), f"Missing: {self._REQUIRED - r.keys()}")

    def test_red_plain_has_all_keys(self):
        r = verify_ip({}, _EXPECTED)
        self.assertTrue(self._REQUIRED.issubset(r.keys()))

    def test_red_dhan_error_has_all_keys(self):
        sdk_resp = {"status": "success", "data": [{"status": "ERROR", "message": "err"}]}
        r = verify_ip(sdk_resp, _EXPECTED)
        self.assertTrue(self._REQUIRED.issubset(r.keys()))

    def test_direct_list_error_has_all_keys(self):
        """List response (direct REST call shape) is also fully handled."""
        r = verify_ip([{"status": "ERROR", "message": "Something went wrong"}], _EXPECTED)
        self.assertTrue(self._REQUIRED.issubset(r.keys()))


if __name__ == "__main__":
    unittest.main()
