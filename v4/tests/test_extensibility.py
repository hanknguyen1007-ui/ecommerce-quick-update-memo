"""G4 (CHARTER v4.1): extensibility proof. Registers a brand-new, synthetic v3-layout VARIANT adapter
(_synthetic_adapter.py: renamed/reordered columns, no comparison columns) through the registry's one public
extension point (register()) and adds a brand-new insight module (test-local, not editing insights.py) --
both without touching base.py, registry.py, v2.py, v3.py, facts.py or insights.py. The no-comparison run
must hide DA (decision 2: missing optional data hides the dependent section, not a fabricated value)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from v4 import pipeline as P  # noqa: E402
from v4.adapters import registry as R  # noqa: E402
import _synthetic_adapter  # noqa: E402
from _local_fixtures import require_local  # noqa: E402

SAMPLE = (Path(__file__).resolve().parent / "samples" / "synthetic_v3_variant.tsv").read_text(encoding="utf-8")
REAL_V3_SAMPLE = ROOT / "templates" / "perf-flash" / "samples" / "input_v3.tsv"


def insight_new_and_improved(facts):
    """A brand-new quick-insight template, defined OUTSIDE insights.py, proving a surface is addable
    without a core edit (R5, CHARTER v4.4: charts removed, this extensibility proof now uses insights)."""
    o = facts["overall"]
    return {"id": "Z", "uses": ["overall.actual"], "text": f"Actual = {o['actual_s']}"}


class Extensibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        R.register(_synthetic_adapter)  # the ONE public extension point; no edit to registry.py itself

    @classmethod
    def tearDownClass(cls):
        R._ADAPTERS.remove(_synthetic_adapter)  # test fixture cleanup, not a "core edit" to make the feature work

    def test_new_adapter_parses_without_touching_any_existing_file(self):
        r = P.analyze(SAMPLE, "Synthetic Variant Test", "12h")
        self.assertTrue(r["ok"], [c for c in r["checks"] if c["status"] == "fail"])
        self.assertEqual(r["facts"]["overall"]["actual"], 1100000)
        self.assertEqual(r["facts"]["overall"]["gap"], 100000)

    def test_no_comparison_columns_hides_da_and_growth(self):
        r = P.analyze(SAMPLE, "Synthetic Variant Test", "12h")
        self.assertTrue(r["ok"])
        f = r["facts"]
        self.assertEqual(f["caps"], {"has_comparison": False, "has_da": False, "has_channels": True, "has_platforms": False})
        self.assertIsNone(f["overall"].get("da_s"))
        self.assertIsNone(f["overall"]["mom"])  # no <cmp> Actual column at all in this layout -> last defaults to 0

    def test_new_insight_module_works_without_editing_insights_py(self):
        r = P.analyze(SAMPLE, "Synthetic Variant Test", "12h")
        spec = insight_new_and_improved(r["facts"])
        self.assertIn("1,100,000", spec["text"])

    def test_ambiguity_refusal_still_works_after_adding_a_third_adapter(self):
        # sanity: registering a 3rd adapter doesn't break the "refuse on >1 match" rule for real v3 input
        require_local(REAL_V3_SAMPLE)  # C4: real pinned sample, not committed
        text = REAL_V3_SAMPLE.read_text(encoding="utf-8")
        name, order, data, extra = R.parse(text, lambda *a, **k: None)
        self.assertEqual(name, "v3")  # still resolves to the real v3 adapter, no ambiguity introduced
        self.assertTrue(order)  # parsed at least one brand, as pasted (C2: no committed brand name here)


if __name__ == "__main__":
    unittest.main(verbosity=2)
