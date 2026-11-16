"""G5 (CHARTER v4.1): refusals tested. Unknown layout and ambiguous column mapping must REFUSE, never guess
(decision 2). Run-rate / comparison-period mismatch across platform blocks is covered in
test_multiplatform.py; this file covers the other two."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from v4 import pipeline as P  # noqa: E402
from v4.adapters.base import Refuse, resolve_columns  # noqa: E402
from v4.adapters import registry as R  # noqa: E402
from _local_fixtures import require_local  # noqa: E402

SAMPLE = ROOT / "templates" / "perf-flash" / "samples" / "input_v3.tsv"


class Refusals(unittest.TestCase):
    def test_unknown_layout_refuses(self):
        garbage = "this is not a report\njust some random prose\nwith no table at all\n"
        r = P.analyze(garbage, "T", "12h")
        self.assertFalse(r["ok"])
        self.assertTrue(any(c["status"] == "fail" for c in r["checks"]))

    def test_unknown_layout_refuses_at_registry_level(self):
        with self.assertRaises(Refuse):
            R.detect("this is not a report\njust some random prose\n")

    def test_ambiguous_column_mapping_refuses(self):
        # two header cells both match the "actual" synonym -- resolve_columns must refuse, not pick one
        header = ["Brand", "Actual", "Actual (duplicate)"]
        with self.assertRaises(Refuse) as cm:
            resolve_columns(header, {"actual": [r"^actual"]}, {"actual"})
        self.assertIn("rõ ràng", cm.exception.reason.casefold())

    def test_ambiguous_mapping_refuses_end_to_end_on_real_v3_header_variant(self):
        # duplicate a v3 required column so two cells both match "actual" -> end-to-end refusal, not a guess
        require_local(SAMPLE)  # C4: real pinned sample, not committed
        v3 = SAMPLE.read_text(encoding="utf-8")
        lines = v3.split("\n")
        for i, ln in enumerate(lines):
            if "Plan Up to Date" in ln and "Total Actual" in ln:
                cells = ln.split("\t")
                idx = cells.index("Total Actual")
                cells.insert(idx + 1, "Total Actual")  # duplicate header cell -> ambiguous "actual" mapping
                lines[i] = "\t".join(cells)
                break
        r = P.analyze("\n".join(lines), "T", "12h 15.11")
        self.assertFalse(r["ok"])

    def test_missing_required_column_refuses(self):
        header_only = "Brand\tKênh\tPlan\n"  # missing GMV plan up to date / Actual
        r = P.analyze(header_only, "T", "12h")
        self.assertFalse(r["ok"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
