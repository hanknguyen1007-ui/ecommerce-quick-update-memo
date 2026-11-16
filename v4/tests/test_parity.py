"""G2 parity smoke test: v4's ported FACTS engine must reproduce the pinned v3 golden facts
(templates/perf-flash/samples/output_v3_facts.json) for templates/perf-flash/samples/input_v3.tsv, using the
same title/timepoint as the pinned run (see samples/REVIEW_v3.md).

C4 (CHARTER v4.3): the real sample/golden and the brand-display translation fixture (C3 -- the golden still
has the old aliased display names baked in; C2 removed that registry from committed code) are both
gitignored, local-only files. On a fresh clone this test SKIPS with an explicit message instead of
crashing with FileNotFoundError, so the suite still runs green."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from v4 import pipeline as P  # noqa: E402

TITLE = "TIKTOK — DOUBLE DAY 11/2026 (Cả campaign)"
TIMEPOINT = "12h 15.11"

NUMERIC_OVERALL_KEYS = ["plan", "ptd", "actual", "last", "gap", "eoc", "eoc_gap", "run_rate", "progress",
                         "y_pp", "z", "mom", "eoc_pct", "req_rem", "req_pace"]

SAMPLE = ROOT / "templates" / "perf-flash" / "samples" / "input_v3.tsv"
GOLDEN = ROOT / "templates" / "perf-flash" / "samples" / "output_v3_facts.json"
FIXTURE = ROOT / "v4" / "tests" / "local_only" / "brand_display_fixture.py"


def main():
    missing = [p.name for p in (SAMPLE, GOLDEN, FIXTURE) if not p.exists()]
    if missing:
        print(f"SKIP: local fixture missing ({', '.join(missing)}) -- this test needs the private pinned "
              f"v3 sample/golden and the local-only brand-display fixture, neither of which is in the repo "
              f"(C4). Nothing to verify on a fresh clone.")
        return

    sys.path.insert(0, str(FIXTURE.parent))
    from brand_display_fixture import V3_RAW_TO_GOLDEN_DISPLAY, rename_brands  # noqa: E402

    text = SAMPLE.read_text(encoding="utf-8")
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))

    r = P.analyze(text, TITLE, TIMEPOINT)
    assert r["ok"], f"analyze() failed: {[c for c in r['checks'] if c['status'] == 'fail']}"
    facts = rename_brands(r["facts"], V3_RAW_TO_GOLDEN_DISPLAY)  # C3: translation lives in the fixture only

    mism = []
    for k in NUMERIC_OVERALL_KEYS:
        a, b = facts["overall"].get(k), golden["overall"].get(k)
        if a is None and b is None:
            continue
        if a is None or b is None or abs(a - b) > 1e-6 * max(1, abs(b)):
            mism.append((k, a, b))
    assert not mism, f"overall mismatch: {mism}"

    for brand, ge in golden["brands"].items():
        assert brand in facts["brands"], f"missing brand {brand}"
        fe = facts["brands"][brand]
        for k in NUMERIC_OVERALL_KEYS:
            a, b = fe.get(k), ge.get(k)
            if a is None and b is None:
                continue
            if a is None or b is None or abs(a - b) > 1e-6 * max(1, abs(b)):
                mism.append((brand, k, a, b))
    assert not mism, f"brand mismatch: {mism}"

    assert facts["brand_order"] == golden["brand_order"], (facts["brand_order"], golden["brand_order"])
    assert facts["overall"]["gap_s"] == golden["overall"]["gap_s"]
    print(f"PARITY OK: {len(golden['brands'])} brands, overall gap {facts['overall']['gap_s']} "
          f"(matches pinned v3 golden to 1e-6 relative tolerance, brand display names translated via the "
          f"local-only fixture per C3)")


if __name__ == "__main__":
    main()
