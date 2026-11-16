"""G1 (local-only, H6/C4: real data, never committed -- SKIPs on a fresh clone). Rendering the two
real pastes reproduces output/brand_v5_golden.md EXACTLY for Docs (CHARTER v5.1: no exception list,
no golden-rewriting step -- the golden itself was corrected at the source of the gap, see
v5/surfaces/text.py's BOLD_RULE docstring and test_rules.py's own bold-rule tests). A single-platform
paste reproduces the same text minus the other platform's section, for EITHER platform alone.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from v5 import pipeline as P  # noqa: E402
from v4.tests._local_fixtures import require_local  # noqa: E402 -- reused read-only, not edited

SHOPEE = ROOT / "output" / "real_brand_shopee_1511.tsv.txt"
TIKTOK = ROOT / "output" / "real_brand_tiktok_1311.tsv"
GOLDEN = ROOT / "output" / "brand_v5_golden.md"


def _golden_text():
    # the golden file's own leading HTML-comment lines (local-only-data notice, never part of the
    # report) are stripped; nothing else about its content is touched.
    lines = [ln for ln in GOLDEN.read_text(encoding="utf-8").split("\n") if not ln.strip().startswith("<!--")]
    return "\n".join(lines).strip() + "\n"


class GoldenLocal(unittest.TestCase):
    def test_combined_paste_matches_golden_exactly(self):
        require_local(SHOPEE, TIKTOK, GOLDEN)
        text = SHOPEE.read_text(encoding="utf-8") + "\n" + TIKTOK.read_text(encoding="utf-8")
        r = P.build(text)
        self.assertTrue(r["ok"], r.get("checks"))
        self.assertEqual(_golden_text(), r["out"]["md"])

    def test_shopee_alone_matches_golden_shopee_section(self):
        require_local(SHOPEE, GOLDEN)
        r = P.build(SHOPEE.read_text(encoding="utf-8"))
        self.assertTrue(r["ok"], r.get("checks"))
        shopee_section = _golden_text().split("---", 2)[1]
        self.assertIn(shopee_section.rstrip("\n"), r["out"]["md"].rstrip("\n"))

    def test_tiktok_alone_matches_golden_tiktok_section(self):
        require_local(TIKTOK, GOLDEN)
        r = P.build(TIKTOK.read_text(encoding="utf-8"))
        self.assertTrue(r["ok"], r.get("checks"))
        tiktok_section = _golden_text().split("---", 2)[2]
        self.assertIn(tiktok_section.rstrip("\n"), r["out"]["md"].rstrip("\n"))


if __name__ == "__main__":
    unittest.main()
