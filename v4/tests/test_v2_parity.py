"""G2, v2 side (CHARTER v4.1: "Same for v2 once built"): v4's v2 adapter + facts vs the frozen, archived
legacy engine (archive/compute.py -- H1, CHARTER v4.2: moved out of every import path core/pipeline.py or
server.py uses; this test imports it directly, by path, as the one place that still exercises it), numeric
parity on input_sample.tsv. Narrower than test_full_parity.py (v2 has no pinned facts JSON golden the way
v3 does -- only output_v3_facts.json exists) -- this compares the two LIVE engines directly instead.
"""
import importlib.util
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from v4 import pipeline as P  # noqa: E402

TITLE = "SHOPEE — MEGA SALE 11.11 (FLASH UPDATE)"
TP = "14h 11.11"
NUMERIC_KEYS = ("plan", "ptd", "actual", "last", "gap", "run_rate", "progress", "z", "mom")


def _load_archived_compute():
    spec = importlib.util.spec_from_file_location("archived_compute", ROOT / "archive" / "compute.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


SAMPLE = ROOT / "templates" / "perf-flash" / "samples" / "input_sample.tsv"
NOTES_SAMPLE = ROOT / "templates" / "perf-flash" / "samples" / "notes_sample.txt"
ARCHIVE_COMPUTE = ROOT / "archive" / "compute.py"


def main():
    missing = [p.name for p in (SAMPLE, NOTES_SAMPLE, ARCHIVE_COMPUTE) if not p.exists()]
    if missing:
        print(f"SKIP: local fixture missing ({', '.join(missing)}) -- this test needs the private pinned "
              f"v2 sample and the archived legacy engine, neither of which is in the repo (C4). Nothing to "
              f"verify on a fresh clone.")
        return
    data = SAMPLE.read_text(encoding="utf-8")
    notes = NOTES_SAMPLE.read_text(encoding="utf-8")
    schema = tomllib.loads((ROOT / "templates" / "perf-flash" / "schema.toml").read_text(encoding="utf-8"))

    legacy_compute = _load_archived_compute()
    legacy = legacy_compute.analyze(data, schema, TITLE, TP)
    assert legacy["ok"], legacy["checks"]
    lf = legacy["facts"]

    r = P.analyze(data, TITLE, TP)
    assert r["ok"], [c for c in r["checks"] if c["status"] == "fail"]
    f = r["facts"]

    assert f["brand_order"] == lf["brand_order"], (f["brand_order"], lf["brand_order"])
    for k in NUMERIC_KEYS:
        a, b = f["overall"].get(k), lf["overall"].get(k)
        if isinstance(b, float):
            assert a is not None and abs(a - b) < 1e-6 * max(1, abs(b)), f"overall.{k}: {a} vs {b}"
        else:
            assert a == b, f"overall.{k}: {a} vs {b}"
    for br in f["brand_order"]:
        for k in NUMERIC_KEYS:
            a, b = f["brands"][br].get(k), lf["brands"][br].get(k)
            if isinstance(b, float):
                assert a is not None and abs(a - b) < 1e-6 * max(1, abs(b)), f"{br}.{k}: {a} vs {b}"
            else:
                assert a == b, f"{br}.{k}: {a} vs {b}"
    assert f["caps"] == {"has_comparison": False, "has_da": False, "has_channels": True, "has_platforms": False}
    print(f"V2 PARITY OK: {len(f['brand_order'])} brands, overall gap {f['overall']['gap']:+,} "
          f"(matches legacy v2 engine to 1e-6 relative tolerance)")


if __name__ == "__main__":
    main()
