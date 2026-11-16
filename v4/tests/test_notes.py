"""G6 + C2 (CHARTER v4.3): notes attach against the brands PRESENT IN THE CURRENT PASTE only -- no
committed brand registry/aliases. Matching: case-insensitive, apostrophe-normalized,
':' optional; a note token contained in exactly one brand name attaches to it (e.g. a short "Alpha" ->
the longer pasted "North Alpha Beauty"); 2+ matches or 0 matches -> unmatched, never dropped silently.
Fictional brand and creator names only (C4)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from v4.surfaces import notes as N  # noqa: E402

BRAND_ORDER = ["North Alpha Beauty", "Velvet Glow", "Maya's Lab"]

LIVE_TEXT = (
    "Alpha Creator Minh live từ 10h\n"
    "Velvet Glow: Hello kitty collab chạy tốt\n"
    "maya's lab hết hàng toner 180ml\n"
    "GARBAGE LINE KHÔNG CÓ BRAND\n"
)


class Notes(unittest.TestCase):
    def test_three_lines_attach_via_containment_colon_and_apostrophe(self):
        r = N.attach(LIVE_TEXT, BRAND_ORDER)
        self.assertIn("Creator Minh live từ 10h", r["brand"]["North Alpha Beauty"])  # "Alpha" contained in "North Alpha Beauty"
        self.assertIn("Hello kitty collab chạy tốt", r["brand"]["Velvet Glow"])
        self.assertIn("hết hàng toner 180ml", r["brand"]["Maya's Lab"])

    def test_garbage_line_not_dropped_silently(self):
        r = N.attach(LIVE_TEXT, BRAND_ORDER)
        lines = [u["line"] for u in r["unmatched"]]
        self.assertIn("GARBAGE LINE KHÔNG CÓ BRAND", lines)

    def test_colon_optional_same_result_either_way(self):
        a = N.attach("North Alpha Beauty OOS toner", BRAND_ORDER)
        b = N.attach("North Alpha Beauty: OOS toner", BRAND_ORDER)
        self.assertEqual(a["brand"], b["brand"])

    def test_short_token_contained_in_longer_pasted_brand_name(self):
        # the charter's own example shape: a short note token ("Alpha") matches the longer brand as pasted
        r = N.attach("Alpha chưa restock", BRAND_ORDER)
        self.assertIn("North Alpha Beauty", r["brand"])

    def test_apostrophe_and_case_insensitive(self):
        r = N.attach("maya’s lab het hang", BRAND_ORDER)
        self.assertIn("Maya's Lab", r["brand"])

    def test_typo_fix_applied(self):
        r = N.attach("Velvet Glow OOS toner", BRAND_ORDER, typos={"OOS": "Out of stock"})
        self.assertIn("Out of stock toner", r["brand"]["Velvet Glow"])

    def test_ambiguous_token_matches_two_brands_blocks_not_guesses(self):
        order = ["Alpha Corp", "Alpha Studio"]
        r = N.attach("Alpha đang chạy tốt", order)
        self.assertEqual(r["brand"], {})
        self.assertEqual(len(r["unmatched"]), 1)
        self.assertEqual(set(r["unmatched"][0]["candidates"]), {"Alpha Corp", "Alpha Studio"})

    def test_no_brand_registry_in_this_module(self):
        # C2: no brand_aliases / hardcoded brand list anywhere in notes.py itself -- it only ever reads
        # the brand names passed in at call time (`brand_order`, from the current paste).
        src = (ROOT / "v4" / "surfaces" / "notes.py").read_text(encoding="utf-8")
        self.assertNotIn("brand_aliases", src)
        self.assertNotIn("import tomllib", src)  # never loads a config file of its own to look brands up in


if __name__ == "__main__":
    unittest.main(verbosity=2)
