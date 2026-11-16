"""Decision 7 + H4 (CHARTER v4.2): quick insights add information the report TEXT does not already state
(no restating overall progress/forecast/best-or-worst-brand); each declares its facts; a template whose
required facts/condition are absent is skipped, never fabricated (decision 2).

H6 note: the charter's own numeric example for input_v3 is verified here by reading those values back OUT
of facts at test time, never typed as a literal in this source file -- so this file carries no real GMV
figure of its own (H6: scrub committed files of real input_v3.tsv/input_sample.tsv figures), while still
proving the insight text matches facts exactly.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core import numfmt as N  # noqa: E402
from v4 import pipeline as P  # noqa: E402
from v4.surfaces import insights as I  # noqa: E402
from _local_fixtures import require_local  # noqa: E402

SAMPLE = ROOT / "templates" / "perf-flash" / "samples" / "input_v3.tsv"


class Insights(unittest.TestCase):
    def setUp(self):
        require_local(SAMPLE)  # C4: real pinned sample, not committed
        text = SAMPLE.read_text(encoding="utf-8")
        r = P.analyze(text, "TIKTOK DOUBLE DAY", "12h 15.11")
        assert r["ok"], r["checks"]
        self.f = r["facts"]
        self.ins = I.generate(self.f)
        self.by_id = {i["id"]: i for i in self.ins}

    def test_every_insight_declares_its_facts(self):
        for i in self.ins:
            self.assertTrue(i["uses"], f"{i['id']} declares no facts paths")

    def test_h4_net_negative_channel_matches_facts(self):
        f = self.f
        leaves = [c for c in f["disp"] if c in f["channels_x"]]
        neg = [c for c in leaves if f["channels_x"][c]["gap"] < 0]
        self.assertEqual(len(neg), 1)  # this sample has exactly one net-negative channel -- the case this insight covers
        c = neg[0]
        cells = [(b, f["brands"][b]["channels"][c]) for b in f["brand_order"] if c in f["brands"][b]["channels"]]
        worst_b, worst_ce = min(cells, key=lambda x: x[1]["gap"])

        self.assertIn("net_negative_channel", self.by_id)
        text = self.by_id["net_negative_channel"]["text"]
        self.assertIn(f["disp"][c], text)
        self.assertIn(f["channels_x"][c]["gap_abs_s"], text)
        self.assertIn(worst_b, text)
        self.assertIn(worst_ce["gap_abs_s"], text)
        self.assertIn("toàn danh mục", text)
        self.assertNotIn("toàn kênh", text)

    def test_h4_da_sign_spread_matches_facts(self):
        f = self.f
        order = f["brand_order"]
        neg = [b for b in order if (f["brands"][b].get("da_pct") or 0) < 0]
        share = sum(f["brands"][b]["contribution"] for b in neg)

        self.assertIn("da_sign_spread", self.by_id)
        text = self.by_id["da_sign_spread"]["text"]
        self.assertIn(f"{len(neg)}/{len(order)}", text)
        self.assertIn(N.pct(share, 1), text)
        self.assertIn("toàn danh mục", text)
        self.assertNotIn("toàn kênh", text)

    def test_h4_does_not_restate_overall_progress_forecast_or_best_worst_brand(self):
        texts = " ".join(i["text"] for i in self.ins)
        self.assertNotIn(self.f["overall"]["progress_s"], texts)
        self.assertNotIn(self.f["overall"]["eoc_pct_s"], texts)
        self.assertNotIn("dẫn đầu", texts)
        self.assertNotIn("chậm tiến độ nhất", texts)


if __name__ == "__main__":
    unittest.main(verbosity=2)
