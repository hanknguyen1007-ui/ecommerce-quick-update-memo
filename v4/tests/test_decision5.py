"""Decision 5 (v4.1 charter): dedicated tests for the 5 wording/threshold changes that intentionally
diverge from the v3 golden (so test_full_parity.py's translate-then-compare correctly excludes them rather
than allowlisting them away). Run with: python -I v4/tests/test_decision5.py
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from v4 import pipeline as P  # noqa: E402
from v4.surfaces import text as S  # noqa: E402
from _local_fixtures import require_local  # noqa: E402

TITLE = "TIKTOK DOUBLE DAY"
TIMEPOINT = "12h 15.11"
SAMPLE = ROOT / "templates" / "perf-flash" / "samples" / "input_v3.tsv"


def _facts():
    require_local(SAMPLE)  # C4: real pinned sample, not committed
    text = SAMPLE.read_text(encoding="utf-8")
    r = P.analyze(text, TITLE, TIMEPOINT)
    assert r["ok"], r["checks"]
    return r["facts"]


class Decision5(unittest.TestCase):
    def setUp(self):
        self.f = _facts()
        self.blocks = S.render(self.f, {"brand": {}})
        self.text = "\n".join(b["s"] for b in self.blocks)

    # 5a: Highlights omit "Fact vận hành" entirely when a highlight brand has no notes.
    def test_5a_highlights_hide_empty_fact_van_hanh(self):
        hl_start = self.text.index("HIGHLIGHTS")
        ll_start = self.text.index("LOWLIGHTS")
        self.assertNotIn("Fact vận hành", self.text[hl_start:ll_start])
        # lowlights keep the placeholder (charter only names Highlights) when a brand has no notes
        self.assertIn("**Fact vận hành:** [cần bổ sung]", self.text[ll_start:])

    # 5b: "{vượt/hụt} plan ngày {Z%}" phrasing, at both overall and channel-clause level.
    def test_5b_vuot_hut_plan_ngay_phrasing(self):
        o = self.f["overall"]
        word = "Vượt" if o["gap"] >= 0 else "Hụt"
        self.assertIn(f"{word} plan ngày", self.text)
        b0 = self.f["brand_order"][0]
        c0 = next(iter(self.f["brands"][b0]["channels"].values()))
        cl = S.clause("X", c0, cmp_label="MoM")
        self.assertRegex(cl, r"(vượt|hụt) plan ngày \d")  # H3 (v4.2): unsigned -- the word carries direction

    # 5c: full VND digits only on the Target line; every other overall VND figure is abbreviated.
    def test_5c_full_digits_only_on_target_line(self):
        o = self.f["overall"]
        target_line = next(b["s"] for b in self.blocks if "Target toàn camp" in b["s"])
        self.assertIn(o["plan_s"], target_line)  # full, comma-grouped digits (not the short/abbreviated form)
        self.assertNotIn(o["actual_s"], self.text)  # full-digit actual_s must NOT appear anywhere
        actual_line = next(b["s"] for b in self.blocks if b["s"].startswith("➔ Actual"))
        self.assertIn(o["actual_sh"], actual_line)  # short form instead, e.g. "3.06B"

    # 5d: base_nho channels use the SAME bullet shape as a normal channel, just a "(base nhỏ)" tag on Z.
    def test_5d_base_nho_same_shape_plus_tag(self):
        e = {"actual_s": "1.0M", "gap_abs_s": "500K", "z_s": "+300.0%", "gap": 1, "small": False,
             "base_nho": True, "mom": None, "da_s": None, "tainted": []}
        cl = S.clause("Chan", e)
        self.assertIn("(base nhỏ)", cl)
        self.assertIn("vượt plan ngày", cl)  # same shape as a normal bullet, not a special VND-first format
        self.assertIn("1.0M VNĐ", cl)
        self.assertIn("500K VNĐ", cl)

    # 5e: brands below the plan-share threshold collapse into ONE "Nhóm brand nhỏ" block, either kind.
    def test_5e_small_brand_collapse_either_kind(self):
        collapsed = [b for b in self.f["brand_order"] if self.f["brands"][b]["collapsed"]]
        self.assertTrue(collapsed)  # this sample has >=1 small brand at the 2% threshold
        kinds = {self.f["brands"][b]["kind"] for b in collapsed}
        # not asserting both kinds are present in THIS sample, but the mechanism must not filter by kind:
        for b in collapsed:
            self.assertLess(self.f["brands"][b]["contribution"], 0.02)
        self.assertIn("NHÓM BRAND NHỎ", self.text)  # H2 (v4.2): own h2 section, not an inline bullet
        self.assertNotIn("Nhóm nhỏ:", self.text)  # old v3 label must not leak into v4 output
        for b in collapsed:
            self.assertNotIn(f"✅ {b}:", self.text)   # not re-listed as a full highlight entry
            self.assertNotIn(f"⚠️ {b} (", self.text)  # nor as a full lowlight entry
            self.assertIn(f"**{b}**:", self.text)     # but does get its own one-line bullet (H2)


class CharterV42(unittest.TestCase):
    """H2/H3 (CHARTER v4.2) on top of decision 5."""

    def setUp(self):
        self.f = _facts()
        self.blocks = S.render(self.f, {"brand": {}})
        self.text = "\n".join(b["s"] for b in self.blocks)

    def test_h3_no_double_negative_anywhere(self):
        import re
        self.assertNotRegex(self.text, r"(hụt|vượt) plan ngày -?\s*[+-]")

    def test_h2_section_is_its_own_h2_after_lowlights(self):
        blocks = self.blocks
        h2s = [i for i, b in enumerate(blocks) if b["t"] == "h2"]
        small_idx = next(i for i, b in enumerate(blocks) if b["s"] == "🟡 NHÓM BRAND NHỎ")
        lowlights_idx = next(i for i, b in enumerate(blocks) if "LOWLIGHTS" in b["s"])
        self.assertIn(small_idx, h2s)
        self.assertGreater(small_idx, lowlights_idx)

    def test_h2_one_bullet_per_small_brand_has_all_four_fields(self):
        small = [b for b in self.f["brand_order"] if self.f["brands"][b].get("collapsed")]
        self.assertTrue(small)
        for b in small:
            line = next(x["s"] for x in self.blocks if x["s"].startswith(f"**{b}**:"))
            self.assertIn("VNĐ", line)
            self.assertIn("plan ngày", line)
            self.assertIn("Forecast", line)


if __name__ == "__main__":
    unittest.main(verbosity=2)
