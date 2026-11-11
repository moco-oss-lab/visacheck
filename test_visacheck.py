"""Tests for visacheck."""

import datetime as dt
import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import visacheck


class TestLookup(unittest.TestCase):
    def test_south_america_route_covered(self):
        for code in ("PE", "BO", "BR", "AR"):
            rec = visacheck.lookup(code)
            self.assertEqual(rec["visa_free_days"], 90)

    def test_lookup_is_case_insensitive(self):
        self.assertEqual(visacheck.lookup("pe")["name"], "Peru")

    def test_unknown_code_rejected(self):
        with self.assertRaises(ValueError):
            visacheck.lookup("XX")

    def test_list_covers_south_america(self):
        codes = {r["code"] for r in visacheck.list_countries()}
        self.assertTrue({"PE", "BO", "BR", "AR", "CL", "UY", "PY"}.issubset(codes))


class TestCheckDestination(unittest.TestCase):
    def test_stay_within_allowance_is_ok(self):
        r = visacheck.check_destination("AR", stay_days=12)
        self.assertEqual(r["status"], "ok")
        self.assertTrue(any("Visa-free" in m for _, m in r["findings"]))

    def test_stay_over_allowance_is_issue(self):
        r = visacheck.check_destination("PE", stay_days=120)
        self.assertEqual(r["status"], "issue")
        self.assertTrue(any("exceeds" in m for _, m in r["findings"]))

    def test_visa_required_country_is_issue(self):
        r = visacheck.check_destination("AU")
        self.assertEqual(r["status"], "issue")
        self.assertIsNone(r["visa_free_days"])

    def test_yellow_fever_required_is_warning(self):
        r = visacheck.check_destination("BO", stay_days=8)
        self.assertEqual(r["status"], "warning")
        self.assertTrue(any("Yellow fever" in m for _, m in r["findings"]))

    def test_passport_validity_ok(self):
        r = visacheck.check_destination(
            "AR", entry_date=dt.date(2027, 3, 1),
            passport_expiry=dt.date(2028, 1, 15))
        self.assertEqual(r["status"], "ok")

    def test_passport_validity_too_short(self):
        r = visacheck.check_destination(
            "PE", entry_date=dt.date(2027, 3, 1),
            passport_expiry=dt.date(2027, 6, 1))
        self.assertEqual(r["status"], "issue")
        self.assertTrue(any("Passport valid" in m for _, m in r["findings"]))

    def test_schengen_three_month_rule(self):
        r = visacheck.check_destination(
            "FR", entry_date=dt.date(2027, 3, 1),
            passport_expiry=dt.date(2027, 5, 1))
        self.assertEqual(r["status"], "issue")


class TestCheckTrip(unittest.TestCase):
    def test_full_south_america_route(self):
        results = visacheck.check_trip(
            ["PE", "BO", "BR", "AR"],
            stays={"PE": 12, "BO": 8, "BR": 10, "AR": 6},
            entry_date=dt.date(2027, 3, 1),
            passport_expiry=dt.date(2028, 6, 1))
        self.assertEqual(len(results), 4)
        self.assertEqual(results[0]["name"], "Peru")
        # Bolivia / Brazil warn about yellow fever; none is an issue.
        self.assertFalse(any(r["status"] == "issue" for r in results))

    def test_json_output_round_trips(self):
        results = visacheck.check_trip(["AR"], stays={"AR": 5})
        data = json.loads(visacheck.format_report(results, json_out=True))
        self.assertEqual(data[0]["code"], "AR")
        self.assertEqual(data[0]["status"], "ok")


class TestCLI(unittest.TestCase):
    def _run(self, *args):
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "visacheck.py")
        return subprocess.run([sys.executable, script, *args],
                              capture_output=True, text=True)

    def test_cli_ok_exit_zero(self):
        proc = self._run("PE", "AR", "--days", "12,6")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("Peru", proc.stdout)
        self.assertIn("Summary", proc.stdout)

    def test_cli_issue_exit_one(self):
        proc = self._run("PE", "--days", "120")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("exceeds", proc.stdout)

    def test_cli_unknown_code_exit_two(self):
        proc = self._run("XX")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("unknown country code", proc.stderr)

    def test_cli_list(self):
        proc = self._run("--list")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("PE", proc.stdout)
        self.assertIn("BR", proc.stdout)

    def test_cli_days_count_mismatch(self):
        proc = self._run("PE", "BO", "--days", "5")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("--days", proc.stderr)

    def test_cli_json_flag(self):
        proc = self._run("PE", "--json")
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertEqual(data[0]["code"], "PE")


if __name__ == "__main__":
    unittest.main()
