"""Tests for dispatch.py (CHARTER v5.1): the single top-level entry point routing a pasted report
to the right engine, never guessing on 0 or 2 matches, with one shared ack_required/warning_messages
envelope regardless of which engine ran."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "v5" / "tests"))

import dispatch as D  # noqa: E402
from v4.adapters.base import Refuse  # noqa: E402
from _helpers import make_block, months_for, valid_values  # noqa: E402

V3_SAMPLE = (ROOT / "templates" / "perf-flash" / "samples" / "synthetic_input_v3.tsv").read_text(encoding="utf-8")
V2_SAMPLE = (ROOT / "templates" / "perf-flash" / "samples" / "synthetic_input_v2.tsv").read_text(encoding="utf-8")

MONTHS = months_for(2026, 11)
CUR = MONTHS.index((2026, 11))


def _brand_monthly_text():
    vals = valid_values(MONTHS, CUR, 15)
    return make_block("Testbrand", "Shopee", (2026, 11, 15), MONTHS, vals)


class Dispatch(unittest.TestCase):
    def test_detects_campaign(self):
        self.assertEqual(D.detect(V3_SAMPLE), "campaign")

    def test_detects_brand_monthly(self):
        self.assertEqual(D.detect(_brand_monthly_text()), "brand-monthly")

    def test_unknown_layout_refuses(self):
        with self.assertRaises(Refuse):
            D.detect("this is not a report\njust some random prose\n")

    def test_ambiguous_input_refuses(self):
        # v3's own sniff() only looks at the first 12 lines, so the "Plan Up to Date" row must come
        # first for this blob to still read as campaign-shaped too
        text = V3_SAMPLE + "\n" + _brand_monthly_text()
        with self.assertRaises(Refuse) as cm:
            D.detect(text)
        self.assertIn("không tự chọn", cm.exception.reason)

    def test_build_routes_campaign_with_no_warnings(self):
        r = D.build([V2_SAMPLE], title="T", timepoint="12h")
        self.assertEqual(r["engine"], "campaign")
        self.assertTrue(r["ok"])
        self.assertIn("md", r["out"])
        self.assertFalse(r["ack_required"])

    def test_build_routes_campaign_with_warnings_sets_ack_required(self):
        r = D.build([V3_SAMPLE], title="T", timepoint="12h")
        self.assertEqual(r["engine"], "campaign")
        self.assertTrue(r["ok"])
        self.assertTrue(r["ack_required"])
        self.assertTrue(r["warning_messages"])

    def test_build_routes_brand_monthly(self):
        r = D.build([_brand_monthly_text()])
        self.assertEqual(r["engine"], "brand-monthly")
        self.assertTrue(r["ok"])
        self.assertIn("md", r["out"])
        self.assertFalse(r["ack_required"])

    def test_build_refuses_unknown_without_crashing(self):
        r = D.build(["garbage, not a report"])
        self.assertFalse(r["ok"])
        self.assertIsNone(r["engine"])
        self.assertTrue(any(c["status"] == "fail" for c in r["checks"]))

    def test_brand_monthly_residual_shift_sets_ack_required(self):
        vals = valid_values(MONTHS, CUR, 15)
        prev = CUR - 1
        sp = vals["self_promotion"][CUR]
        import calendar
        prev_days = calendar.monthrange(*MONTHS[prev])[1]
        ls_prev_da = vals["livestream"][prev] / prev_days
        vals["livestream"][CUR] = round(ls_prev_da * 0.5 * 15)
        vals["showcase"][CUR] = sp - vals["livestream"][CUR] - vals["video"][CUR]
        text = make_block("Testbrand", "Shopee", (2026, 11, 15), MONTHS, vals)
        r = D.build([text])
        self.assertTrue(r["ok"])
        self.assertTrue(r["ack_required"])
        self.assertTrue(r["warning_messages"])


if __name__ == "__main__":
    unittest.main()
