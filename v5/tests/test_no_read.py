"""G4: corrupting every derived row the sheet carries (decision 3's forbidden list) leaves the
output byte-identical -- proof the adapter never reads them, only the 9 raw rows in config.LABELS."""
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
N = len(MONTHS)

DERIVED_ROWS = [
    ("DAGMV MoM Growth Rate", ["-999%"] * N),
    ("Self Promotion Contribution", ["1%"] * N),
    ("Affiliate Contribution", ["999%"] * N),
    ("Shopping Ads Contribution", ["0%"] * N),
    ("% Livestream", ["-50%"] * N),
    ("% Video", ["-50%"] * N),
    ("% Showcase&Other", ["-50%"] * N),
    ("% Affiliate", ["-50%"] * N),
    ("Commission", ["999%"] * N),
    ("PoP", ["#DIV/0!"] * N),
    ("Ads Take rate", ["999%"] * N),
    ("ROAS", ["-1"] * N),
    ("ROI", ["-1"] * N),
    ("Growth", ["999%"] * N),
]


class NoReadGuarantee(unittest.TestCase):
    def test_corrupting_every_derived_row_does_not_change_output(self):
        vals = valid_values(MONTHS, CUR, 15)
        clean = make_block("Testbrand", "Shopee", (2026, 11, 15), MONTHS, vals)
        corrupted = make_block("Testbrand", "Shopee", (2026, 11, 15), MONTHS, vals, extra_rows=DERIVED_ROWS)
        r_clean = P.build(clean)
        r_corrupted = P.build(corrupted)
        self.assertTrue(r_clean["ok"] and r_corrupted["ok"])
        self.assertEqual(r_clean["out"]["md"], r_corrupted["out"]["md"])


if __name__ == "__main__":
    unittest.main()
