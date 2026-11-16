"""G2: a paste with scratch cells, a hidden extra column, and a future (zero) month column still
produces the SAME output as the clean fixture -- the adapter only ever reads the 9 raw rows by exact
label (decision 2/3), so none of this can move the needle."""
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


class Robustness(unittest.TestCase):
    def test_scratch_cells_and_future_month_do_not_change_output(self):
        vals = valid_values(MONTHS, CUR, 15)
        clean = make_block("Testbrand", "Shopee", (2026, 11, 15), MONTHS, vals)
        r_clean = P.build(clean)
        self.assertTrue(r_clean["ok"])

        # add a future (Dec 2026) column, all zero -- "not yet happened" (decision 2)
        months2 = MONTHS + [(2026, 12)]
        vals2 = {k: v + [0] for k, v in vals.items()}
        noisy = make_block("Testbrand", "Shopee", (2026, 11, 15), months2, vals2,
                            extra_rows=[("DAGMV MoM Growth Rate", ["#DIV/0!"] * len(months2)),
                                        ("", ["38%"] + [""] * (len(months2) - 1)),
                                        ("Flash sale GMV", [""] * len(months2)),
                                        ("Growth", ["0%"] * len(months2))])
        r_noisy = P.build(noisy)
        self.assertTrue(r_noisy["ok"])
        self.assertEqual(r_clean["out"]["md"], r_noisy["out"]["md"])

    def test_missing_oldest_hidden_column_does_not_change_output(self):
        vals = valid_values(MONTHS, CUR, 15)
        full = make_block("Testbrand", "Shopee", (2026, 11, 15), MONTHS, vals)
        r_full = P.build(full)

        trimmed_months = MONTHS[1:]  # drop the oldest ("hidden") column -- never read anyway
        trimmed_vals = {k: v[1:] for k, v in vals.items()}
        trimmed = make_block("Testbrand", "Shopee", (2026, 11, 15), trimmed_months, trimmed_vals)
        r_trimmed = P.build(trimmed)
        self.assertTrue(r_trimmed["ok"])
        self.assertEqual(r_full["out"]["md"], r_trimmed["out"]["md"])

    def test_single_platform_paste_equals_combined_minus_other_platform(self):
        vals = valid_values(MONTHS, CUR, 15)
        shopee = make_block("Testbrand", "Shopee", (2026, 11, 15), MONTHS, vals)
        tiktok = make_block("Testbrand", "Tiktok", (2026, 11, 15), MONTHS, vals)
        combined = P.build(shopee + "\n" + tiktok)
        solo = P.build(shopee)
        self.assertTrue(combined["ok"] and solo["ok"])
        solo_body = solo["out"]["md"].split("---", 1)[1]
        combined_body = combined["out"]["md"].split("---", 1)[1]
        self.assertTrue(combined_body.startswith(solo_body.rstrip("\n")))


if __name__ == "__main__":
    unittest.main()
