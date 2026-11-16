"""Decision 3 / G5 (CHARTER v4.1): multi-platform combine. Several pasted blocks (one per platform) ->
combined text report (brand totals summed), and pipeline.combine() REFUSES (never averages/guesses) when
platforms disagree on run-rate or comparison period. R5 (CHARTER v4.4): charts removed -- the per-platform
split itself is no longer kept as a fact; only caps.has_platforms + the combined totals survive."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from v4 import pipeline as P  # noqa: E402
from _local_fixtures import require_local  # noqa: E402

SAMPLE = ROOT / "templates" / "perf-flash" / "samples" / "input_v3.tsv"

HEADER = "Brand\tKênh\tPlan\tGMV plan up to date\tActual 11/11\tActual tháng trước\n"


def _rows(brand, total, aff, ss, live, vid, show):
    def r(ch, v):
        plan, ptd, actual = v
        return f"{brand}\t{ch}\t{plan}\t{ptd}\t{actual}\t0\n"
    return (r("TOTAL", total) + r("Affiliate", aff) + r("Self-sell", ss)
            + r("LIVE nội bộ", live) + r("Video nội bộ", vid) + r("Showcase", show))


def _block(brand, run_rate_pct):
    # plan=1,000,000; ptd = plan*run_rate; actual a bit above ptd. Affiliate+Self-sell=TOTAL, LIVE+Video+Showcase=Self-sell.
    plan = 1_000_000
    ptd = round(plan * run_rate_pct / 100)
    actual = ptd + 50_000
    aff_plan, ss_plan = plan // 2, plan // 2
    aff_ptd, ss_ptd = ptd // 2, ptd - ptd // 2
    aff_act, ss_act = actual // 2, actual - actual // 2
    live_plan, vid_plan, show_plan = ss_plan // 3, ss_plan // 3, ss_plan - 2 * (ss_plan // 3)
    live_ptd, vid_ptd, show_ptd = ss_ptd // 3, ss_ptd // 3, ss_ptd - 2 * (ss_ptd // 3)
    live_act, vid_act, show_act = ss_act // 3, ss_act // 3, ss_act - 2 * (ss_act // 3)
    return HEADER + _rows(brand, (plan, ptd, actual), (aff_plan, aff_ptd, aff_act), (ss_plan, ss_ptd, ss_act),
                          (live_plan, live_ptd, live_act), (vid_plan, vid_ptd, vid_act), (show_plan, show_ptd, show_act))


class MultiPlatform(unittest.TestCase):
    def test_same_run_rate_combines_and_sums_brand_totals(self):
        tiktok = _block("Acme", 50.0)
        shopee = _block("Acme", 50.0)
        r = P.combine([tiktok, shopee], "Multi-platform test", "12h")
        self.assertTrue(r["ok"], [c for c in r["checks"] if c["status"] == "fail"])
        f = r["facts"]
        self.assertTrue(f["caps"]["has_platforms"])
        self.assertEqual(f["overall"]["actual"], 2 * (500_000 + 50_000))  # both blocks summed

    def test_mismatched_run_rate_refuses_not_averages(self):
        tiktok = _block("Acme", 50.0)
        shopee = _block("Acme", 70.0)
        r = P.combine([tiktok, shopee], "Multi-platform test", "12h")
        self.assertFalse(r["ok"])
        self.assertTrue(any("Run-rate" in c["name"] for c in r["checks"]))

    def test_mismatched_cmp_label_refuses(self):
        require_local(SAMPLE)  # C4: real pinned sample, not committed
        v3 = SAMPLE.read_text(encoding="utf-8")
        v3_other_cmp = v3.replace("GMV vs Tháng 10/2026", "GMV vs Tháng 09/2026")
        r = P.combine([v3, v3_other_cmp], "Multi-platform test", "12h 15.11")
        self.assertFalse(r["ok"])
        self.assertTrue(any("so sánh" in c["name"] for c in r["checks"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
