"""Refusals (decision 1/2/4/5): unknown layout, mismatched brand/duplicate platform across blocks,
Time-Runrate-vs-Date-update mismatch, and the two integrity asserts -- never a guess, never a partial
report (G2's "broken identity, runrate mismatch, two brands, duplicate platform -> clear refusal")."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from v4.adapters.base import Refuse  # noqa: E402
from v5 import pipeline as P  # noqa: E402
from v5.adapters import brand_monthly as A  # noqa: E402
from _helpers import make_block, months_for, valid_values  # noqa: E402

MONTHS = months_for(2026, 11)
CUR = MONTHS.index((2026, 11))


def _block(brand="Testbrand", platform="Shopee", **kw):
    vals = valid_values(MONTHS, CUR, 15, **kw)
    return make_block(brand, platform, (2026, 11, 15), MONTHS, vals)


class Refusals(unittest.TestCase):
    def test_unknown_layout_refuses(self):
        r = P.build("this is not a report\njust some random prose\n")
        self.assertFalse(r["ok"])
        self.assertTrue(any(c["status"] == "fail" for c in r["checks"]))

    def test_unknown_layout_refuses_at_adapter_level(self):
        with self.assertRaises(Refuse):
            A.parse("this is not a report\njust some random prose\n")

    def test_different_brand_across_blocks_refuses(self):
        text = _block(brand="Testbrand") + "\n" + _block(brand="Otherbrand", platform="Tiktok")
        with self.assertRaises(Refuse) as cm:
            A.parse(text)
        self.assertIn("brand khác nhau", cm.exception.reason)

    def test_duplicate_platform_refuses(self):
        text = _block(platform="Shopee") + "\n" + _block(platform="Shopee")
        with self.assertRaises(Refuse) as cm:
            A.parse(text)
        self.assertIn("trùng platform", cm.exception.reason)

    def test_runrate_mismatch_refuses(self):
        vals = valid_values(MONTHS, CUR, 15)
        vals["time_runrate"][CUR] = 0.90  # sheet claims 90% elapsed, Date update says day 15 (50%)
        text = make_block("Testbrand", "Shopee", (2026, 11, 15), MONTHS, vals)
        r = P.build(text)
        self.assertFalse(r["ok"])
        self.assertIn("Time Runrate", r["checks"][0]["detail"])

    def test_sp_plus_affiliate_must_equal_gmv(self):
        vals = valid_values(MONTHS, CUR, 15)
        vals["self_promotion"][CUR] += 1000  # breaks SP + Affiliate == GMV by more than +-1 VND
        text = make_block("Testbrand", "Shopee", (2026, 11, 15), MONTHS, vals)
        r = P.build(text)
        self.assertFalse(r["ok"])

    def test_detailed_must_sum_to_self_promotion(self):
        vals = valid_values(MONTHS, CUR, 15)
        vals["livestream"][CUR] += 1000  # breaks LS + Video + Showcase == SP
        text = make_block("Testbrand", "Shopee", (2026, 11, 15), MONTHS, vals)
        r = P.build(text)
        self.assertFalse(r["ok"])

    def test_missing_required_row_refuses(self):
        text = _block().rsplit("\n", 1)[0]  # drop the last row (Total_Ads expense)
        with self.assertRaises(Refuse) as cm:
            A.parse(text)
        self.assertIn("thiếu cột bắt buộc", cm.exception.reason)


if __name__ == "__main__":
    unittest.main()
