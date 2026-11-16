"""R1-R3, R6 (CHARTER v4.4): real-world paste robustness. The two real TikTok 20h pastes (local-only,
output/debug_input_20h.tsv without "↳", output/debug_input_20h_arrow.tsv with "↳") both used to fail --
channel rows read as brands without an arrow (R1), and the "↳" version failed integrity on a derived-plan
rounding amplification (R2). Both must now pass and render. Committed synthetic twins (fictional brands,
proper diacritics) reproduce the same two shapes, including a deliberate 1-VND SOURCE rounding, so the
suite has non-real coverage of the same fix even without the local-only files."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from v4 import pipeline as P  # noqa: E402
from _local_fixtures import require_local  # noqa: E402

TITLE = "TIKTOK — DOUBLE DAY 11/2026 (Cả campaign)"
TIMEPOINT = "20h 15.11"

REAL_NO_ARROW = ROOT / "output" / "debug_input_20h.tsv"
REAL_ARROW = ROOT / "output" / "debug_input_20h_arrow.tsv"
SYN_NO_ARROW = ROOT / "templates" / "perf-flash" / "samples" / "synthetic_input_v3_20h.tsv"
SYN_ARROW = ROOT / "templates" / "perf-flash" / "samples" / "synthetic_input_v3_20h_arrow.tsv"
SYN_TITLE = "SYNTHETIC — DEMO 20H 11/2026 (Cả campaign)"


class RealPasteRobustness(unittest.TestCase):
    # ---------- real pastes (local-only, skip on a fresh clone) ----------
    def test_real_no_arrow_paste_parses_and_renders(self):
        require_local(REAL_NO_ARROW)
        text = REAL_NO_ARROW.read_text(encoding="utf-8")
        r = P.build(text, TITLE, TIMEPOINT, "")
        self.assertTrue(r["ok"], [c for c in r["checks"] if c["status"] == "fail"])
        self.assertTrue(r["out"]["md"])
        self.assertTrue(r["out"]["html_msg"])

    def test_real_arrow_paste_parses_and_renders(self):
        require_local(REAL_ARROW)
        text = REAL_ARROW.read_text(encoding="utf-8")
        r = P.build(text, TITLE, TIMEPOINT, "")
        self.assertTrue(r["ok"], [c for c in r["checks"] if c["status"] == "fail"])
        self.assertTrue(r["out"]["md"])

    def test_both_real_pastes_agree(self):
        require_local(REAL_NO_ARROW, REAL_ARROW)
        a = P.analyze(REAL_NO_ARROW.read_text(encoding="utf-8"), TITLE, TIMEPOINT)
        b = P.analyze(REAL_ARROW.read_text(encoding="utf-8"), TITLE, TIMEPOINT)
        self.assertTrue(a["ok"] and b["ok"])
        self.assertEqual(a["facts"]["brand_order"], b["facts"]["brand_order"])
        self.assertEqual(a["facts"]["overall"]["gap"], b["facts"]["overall"]["gap"])

    def test_real_paste_suggests_correct_title_and_timepoint(self):
        require_local(REAL_NO_ARROW)
        r = P.analyze(REAL_NO_ARROW.read_text(encoding="utf-8"), "", "")
        self.assertEqual(r["suggest"]["title"], TITLE)
        self.assertEqual(r["suggest"]["timepoint"], "20h 15.11")

    # ---------- synthetic twins (committed, fictional brands, proper diacritics) ----------
    def test_synthetic_no_arrow_twin_parses(self):
        text = SYN_NO_ARROW.read_text(encoding="utf-8")
        r = P.build(text, SYN_TITLE, "20h 15.11", "")
        self.assertTrue(r["ok"], [c for c in r["checks"] if c["status"] == "fail"])
        self.assertEqual(r["facts"]["brand_order"], ["Brand One", "Brand Two"])

    def test_synthetic_arrow_twin_parses_same_as_no_arrow(self):
        no_arrow = P.analyze(SYN_NO_ARROW.read_text(encoding="utf-8"), SYN_TITLE, "20h 15.11")
        arrow = P.analyze(SYN_ARROW.read_text(encoding="utf-8"), SYN_TITLE, "20h 15.11")
        self.assertTrue(no_arrow["ok"] and arrow["ok"])
        self.assertEqual(no_arrow["facts"]["overall"]["gap"], arrow["facts"]["overall"]["gap"])

    def test_synthetic_twin_1_vnd_source_rounding_tolerated(self):
        # Brand Two's TOTAL ptd is deliberately 1 VND off from Affiliate+Self-sell -- within tolerance,
        # must not fail (R2: tolerance applies to source columns; this is exactly that case, not derived).
        r = P.analyze(SYN_NO_ARROW.read_text(encoding="utf-8"), SYN_TITLE, "20h 15.11")
        self.assertTrue(r["ok"], [c for c in r["checks"] if c["status"] == "fail"])

    def test_synthetic_twins_use_proper_vietnamese_diacritics(self):
        for p in (SYN_NO_ARROW, SYN_ARROW):
            text = p.read_text(encoding="utf-8")
            self.assertIn("Tháng", text)
            self.assertNotIn("Thang ", text)  # no ASCII-stripped diacritics


if __name__ == "__main__":
    unittest.main(verbosity=2)
