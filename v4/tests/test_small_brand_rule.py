"""S1-S3 (CHARTER v4.6, Hiếu's decision): a brand collapses into "Nhóm brand nhỏ" only if BOTH its plan
share AND its actual share of the portfolio (same paste; multi-platform combine already merges totals
before this runs) are below the threshold -- not plan share alone. Motivating bug: a live TikTok 20h run
hid two brands in the small-brand group because their PLAN share was < 2% although their ACTUAL share had
grown past it, while another brand with a higher plan share but a shrunk actual share stayed a full block
-- plan-only importance stayed blind to brands that had grown. facts.py now exposes plan_share/actual_share
on every brand regardless of collapse outcome (S1). The real brand names involved are LOCAL-ONLY (see
local_only/small_brand_membership_fixture.py, gitignored, same category as the real samples); this file
itself never names them."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from v4 import pipeline as P  # noqa: E402
from _local_fixtures import require_local  # noqa: E402

BOUNDARY = ROOT / "templates" / "perf-flash" / "samples" / "synthetic_input_v3_small_brand_boundary.tsv"
REAL_20H_NO_ARROW = ROOT / "output" / "debug_input_20h.tsv"
REAL_20H_ARROW = ROOT / "output" / "debug_input_20h_arrow.tsv"
REAL_12H = ROOT / "templates" / "perf-flash" / "samples" / "input_v3.tsv"
MEMBERSHIP_FIXTURE = ROOT / "v4" / "tests" / "local_only" / "small_brand_membership_fixture.py"


def _boundary_facts():
    text = BOUNDARY.read_text(encoding="utf-8")
    r = P.analyze(text, "T", "20h 15.11")
    assert r["ok"], [c for c in r["checks"] if c["status"] == "fail"]
    return r["facts"]


class SyntheticBoundary(unittest.TestCase):
    """S3: committed fictional-brand sample covering the three boundary cases."""

    @classmethod
    def setUpClass(cls):
        cls.f = _boundary_facts()
        cls.B = cls.f["brands"]

    def test_s1_facts_expose_both_shares_on_every_brand(self):
        for b in self.f["brand_order"]:
            e = self.B[b]
            self.assertIn("plan_share", e)
            self.assertIn("actual_share", e)
            self.assertIsInstance(e["plan_share"], float)
            self.assertIsInstance(e["actual_share"], float)

    def test_plan_below_threshold_actual_above_is_full_block(self):
        # Brand Grow: plan share 1% (<2%), actual share 3% (>=2%) -- must NOT collapse.
        e = self.B["Brand Grow"]
        self.assertLess(e["plan_share"], 0.02)
        self.assertGreaterEqual(e["actual_share"], 0.02)
        self.assertFalse(e["collapsed"])

    def test_both_below_threshold_is_small(self):
        # Brand Tiny: plan share 1%, actual share 1% -- both below -- collapses.
        e = self.B["Brand Tiny"]
        self.assertLess(e["plan_share"], 0.02)
        self.assertLess(e["actual_share"], 0.02)
        self.assertTrue(e["collapsed"])

    def test_exactly_at_threshold_is_full_block_not_small(self):
        # Brand Exact: plan share and actual share both EXACTLY 2% -- "< T" is false at equality, so a
        # full block (the rule is strict: a brand sitting exactly on the line is not "below" it).
        e = self.B["Brand Exact"]
        self.assertEqual(e["plan_share"], 0.02)
        self.assertEqual(e["actual_share"], 0.02)
        self.assertFalse(e["collapsed"])

    def test_only_the_both_below_brand_is_small(self):
        small = [b for b in self.f["brand_order"] if self.B[b]["collapsed"]]
        self.assertEqual(small, ["Brand Tiny"])


class RealPasteMembership(unittest.TestCase):
    """S2: expected Highlights/Lowlights/small-brand membership on the real local-only pastes. Real brand
    names come only from the gitignored local_only fixture; skips (both for the missing paste and for the
    missing fixture) rather than hardcoding any real name in this committed file."""

    def _expected(self):
        require_local(MEMBERSHIP_FIXTURE)
        sys.path.insert(0, str(MEMBERSHIP_FIXTURE.parent))
        from small_brand_membership_fixture import EXPECTED  # noqa: E402
        return EXPECTED

    def _check(self, text, expected):
        r = P.analyze(text, "T", "TP")
        self.assertTrue(r["ok"], [c for c in r["checks"] if c["status"] == "fail"])
        f = r["facts"]
        B = f["brands"]
        full_highlights = [b for b in f["highlights"] if not B[b]["collapsed"]]
        full_lowlights = [b for b in f["lowlights"] if not B[b]["collapsed"]]
        small = [b for b in f["brand_order"] if B[b]["collapsed"]]
        for b in expected["full_highlights_includes"]:
            self.assertIn(b, full_highlights)
        self.assertEqual(small, expected["small_only"])
        im = next(b for b in f["brand_order"] if b.endswith(expected["full_lowlight_name_suffix"]))
        self.assertIn(im, full_lowlights)
        # ordered by gap with the other highlights: the newly-full brands take their place by gap, not
        # shunted to the end or given a group of their own.
        gaps = [B[b]["gap"] for b in full_highlights]
        self.assertEqual(gaps, sorted(gaps, reverse=True))
        return f

    def test_20h_no_arrow(self):
        require_local(REAL_20H_NO_ARROW)
        self._check(REAL_20H_NO_ARROW.read_text(encoding="utf-8"), self._expected())

    def test_20h_arrow(self):
        require_local(REAL_20H_ARROW)
        self._check(REAL_20H_ARROW.read_text(encoding="utf-8"), self._expected())

    def test_12h(self):
        require_local(REAL_12H)
        self._check(REAL_12H.read_text(encoding="utf-8"), self._expected())


if __name__ == "__main__":
    unittest.main(verbosity=2)
