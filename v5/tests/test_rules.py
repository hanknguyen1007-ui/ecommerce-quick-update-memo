"""G3: one test per locked rule (decisions 6, 7, 9, 11, 12), on synthetic data built to land exactly
on each rule's condition."""
import calendar
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from v5 import pipeline as P  # noqa: E402
from _helpers import make_block, months_for, valid_values  # noqa: E402

MONTHS = months_for(2026, 11)
CUR = MONTHS.index((2026, 11))
PREV = CUR - 1
PREV_DAYS = calendar.monthrange(*MONTHS[PREV])[1]
METRICS = ("gmv", "self_promotion", "affiliate", "ads_gmv", "livestream", "video", "showcase",
           "affiliate_cost", "ads_cost")


def _text(brand="Testbrand", platform="Shopee", elapsed=15, **kw):
    vals = valid_values(MONTHS, CUR, elapsed, **kw)
    return make_block(brand, platform, (2026, 11, 15), MONTHS, vals)


def _scale_cur_da(vals, key, factor, elapsed=15):
    """Rewrite vals[key][CUR] so its DA is exactly `factor` times vals[key][PREV]'s DA -- a MoM %
    change of (factor - 1), independent of the flat baseline's day-count arithmetic."""
    prev_da = vals[key][PREV] / PREV_DAYS
    vals[key][CUR] = round(prev_da * factor * elapsed)


def _scale_all_cur_da(vals, factor, elapsed=15):
    """Same as _scale_cur_da but on every raw row at once, so every decision-5 integrity ratio
    (SP + Affiliate == GMV, LS + Video + Showcase == SP) still holds after the MoM swing."""
    for key in METRICS:
        _scale_cur_da(vals, key, factor, elapsed)


class Rules(unittest.TestCase):
    def test_qoq_hidden_when_previous_quarter_incomplete(self):
        # current month = Jan 2026, paste only reaches back to Nov 2025 -> previous quarter (Q4 2025:
        # Oct/Nov/Dec) is NOT fully in the paste (Oct 2025 missing)
        months = months_for(2026, 1, n_before=3)
        cur = months.index((2026, 1))
        vals = valid_values(months, cur, 10)
        text = make_block("Testbrand", "Shopee", (2026, 1, 10), months, vals)
        r = P.build(text)
        self.assertTrue(r["ok"])
        pf = r["facts"]["platforms"][0]
        self.assertFalse(pf["qoq_available"])
        self.assertNotIn("QoQ", r["out"]["md"].split("### 1.")[0])

    def test_significance_gate_hides_shares_below_5pct_and_shows_above(self):
        vals = valid_values(MONTHS, CUR, 15)
        _scale_all_cur_da(vals, 1.02)  # GMV MoM = +2% < 5%: shares must stay hidden
        text = make_block("Testbrand", "Shopee", (2026, 11, 15), MONTHS, vals)
        r = P.build(text)
        self.assertTrue(r["ok"])
        self.assertNotIn("mức tăng", r["out"]["md"])
        self.assertNotIn("mức giảm", r["out"]["md"])

        vals2 = valid_values(MONTHS, CUR, 15)
        _scale_all_cur_da(vals2, 1.20)  # GMV MoM = +20% >= 5%: shares must show
        text2 = make_block("Testbrand", "Shopee", (2026, 11, 15), MONTHS, vals2)
        r2 = P.build(text2)
        self.assertTrue(r2["ok"])
        self.assertIn("mức tăng", r2["out"]["md"])

    def test_gmv_down_wording(self):
        vals = valid_values(MONTHS, CUR, 15)
        _scale_all_cur_da(vals, 0.5)  # GMV MoM falls sharply
        text = make_block("Testbrand", "Shopee", (2026, 11, 15), MONTHS, vals)
        r = P.build(text)
        self.assertTrue(r["ok"])
        self.assertIn("MoM: 🔴", r["out"]["md"].split("### 1.")[0])
        self.assertIn("mức giảm", r["out"]["md"])

    def test_small_base_detail_line(self):
        text = _text(video_share=0.001)  # Video far under 2% of platform GMV
        r = P.build(text)
        pf = r["facts"]["platforms"][0]
        self.assertTrue(pf["detailed"]["video"]["small_base"])
        self.assertIn("base nhỏ", r["out"]["md"])

    def test_residual_shift_flag_fires(self):
        vals = valid_values(MONTHS, CUR, 15)
        sp = vals["self_promotion"][CUR]
        _scale_cur_da(vals, "livestream", 0.5)  # Livestream DA falls 50% (>= 30%) MoM
        _scale_cur_da(vals, "video", 1.0)  # Video DA unchanged
        vals["showcase"][CUR] = sp - vals["livestream"][CUR] - vals["video"][CUR]  # Showcase rises to compensate
        text = make_block("Testbrand", "Shopee", (2026, 11, 15), MONTHS, vals)
        r = P.build(text)
        self.assertTrue(r["ok"])
        self.assertTrue(r["facts"]["platforms"][0]["flags"]["residual_shift"])
        self.assertIn("⚠️", r["out"]["md"])

    def test_residual_shift_flag_does_not_fire_when_livestream_rises(self):
        vals = valid_values(MONTHS, CUR, 15)
        text = make_block("Testbrand", "Shopee", (2026, 11, 15), MONTHS, vals)  # flat run-rate: LS unchanged
        r = P.build(text)
        self.assertTrue(r["ok"])
        self.assertFalse(r["facts"]["platforms"][0]["flags"]["residual_shift"])
        self.assertNotIn("⚠️", r["out"]["md"])

    def test_giu_wording_when_ads_share_barely_moves(self):
        text = _text(ads_share=0.5)  # flat run-rate -> T11 Ads share == T10 Ads share
        r = P.build(text)
        self.assertIn("giữ", r["out"]["md"])

    def test_gan_bang_wording_when_mom_growth_rates_are_close(self):
        vals = valid_values(MONTHS, CUR, 15, ads_share=0.5)
        for key in METRICS:  # both Ads and Organic grow MoM, at nearly the same rate
            _scale_cur_da(vals, key, 1.30)
        text = make_block("Testbrand", "Shopee", (2026, 11, 15), MONTHS, vals)
        r = P.build(text)
        self.assertTrue(r["ok"])
        self.assertIn("gần bằng nhau", r["out"]["md"])

    def test_quick_recap_trims_highlights_before_lowlights(self):
        # two platforms, both strongly growing on every block both periods -> >10 recap bullets if untrimmed
        vals = valid_values(MONTHS, CUR, 15, sp_share=0.6, ads_share=0.5)
        for i in (PREV, CUR - 2, CUR - 3, CUR - 4):
            for key in METRICS:
                vals[key][i] = round(vals[key][i] * 0.5)
        shopee = make_block("Testbrand", "Shopee", (2026, 11, 15), MONTHS, vals)
        tiktok = make_block("Testbrand", "Tiktok", (2026, 11, 15), MONTHS, vals)
        r = P.build(shopee + "\n" + tiktok)
        self.assertTrue(r["ok"])
        recap = r["out"]["md"].split("---", 1)[0]
        bullets = recap.count("\n* ")
        self.assertLessEqual(bullets, 10)


if __name__ == "__main__":
    unittest.main()
