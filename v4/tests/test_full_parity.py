"""G2 (CHARTER v4.1): "translate then compare exactly" full facts diff against the pinned v3 golden
(templates/perf-flash/samples/output_v3_facts.json). Renamed/relocated fields (S2) are not allowlisted away
any more -- they are *reconstructed* through the real surfaces.text function that owns that wording
(impact_label, plaus_message, cmp_phrases, surfaces.text.marked for the ⚠️ taint glyph) and THEN compared
for exact equality against the golden. A key only goes in ALLOW when it is genuinely new in v4 and absent
from the pre-v4 golden, or is an object outside facts.compute()'s own output (xcheck/checks) -- charter caps
this at <= 4 entries. Decision-5 (v4.1) wording/threshold changes that deliberately diverge from the v3
golden (clause's new shape, the small-brand collapse threshold/scope) are NOT allowlisted here either: they
are excluded from this translate-then-compare walk and verified by their own dedicated tests instead
(test_decision5.py), so this file never hides a real divergence behind "that's just decision 5".
"""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from v4 import pipeline as P  # noqa: E402
from v4.surfaces import text as S  # noqa: E402

TITLE = "TIKTOK — DOUBLE DAY 11/2026 (Cả campaign)"
TIMEPOINT = "12h 15.11"

# <= 4 entries (charter G2 cap): only keys genuinely new in v4 and absent from the pre-v4 golden, or objects
# outside facts.compute()'s own output.
ALLOW = {
    "caps": "new in v4 (capability flags: has_comparison/has_da/has_channels/has_platforms) -- not present in the pre-v4 golden",
    "platform": "new in v4 (decision 3: multi-platform support) -- not present in the pre-v4 golden; this sample has no Platform header value so it is None, which is fine",
    "xcheck": "produced by pipeline/checks reporting, not facts.compute() -- not part of this facts-only diff",
    "checks": "same object as the live checks list; not part of facts.compute()'s own output, covered by test_parity's checks assertions instead",
}

# Paths EXCLUDED from this walk because decision 5 (v4.1) deliberately changed them from the v3 golden's
# behavior/wording -- not a translation gap, a real behavior change. Each has its own dedicated test.
DECISION_DIVERGENCE = {
    "brands.*.channels.*.clause": "decision 5b/5d: new bullet shape ('{vượt/hụt} plan ngày Z%', base_nho same "
        "shape + tag) -- see test_decision5.py::test_clause_5b_5d_wording",
    "brands.*.collapsed": "decision 5e: threshold 1%->2% (small_brand_share_v4) + applies to highlight brands "
        "too, not lowlight-only -- see test_decision5.py::test_5e_small_brand_collapse_either_kind",
}


def _allowed(path, table):
    parts = path.split(".")
    for pat in table:
        pp = pat.split(".")
        if len(pp) != len(parts):
            continue
        if all(a == "*" or a == b for a, b in zip(pp, parts)):
            return True
    return False


def _excluded(path):
    return _allowed(path, ALLOW) or _allowed(path, DECISION_DIVERGENCE)


def _walk(path, a, b, out):
    if _excluded(path):
        return
    if isinstance(b, dict):
        if not isinstance(a, dict):
            out.append((path, "type", type(a).__name__, "dict"))
            return
        for k, bv in b.items():
            p = f"{path}.{k}" if path else k
            if _excluded(p):
                continue
            if k not in a:
                out.append((p, "missing_in_v4", None, bv))
                continue
            _walk(p, a[k], bv, out)
    elif isinstance(b, list):
        if not isinstance(a, list):
            out.append((path, "type", type(a).__name__, "list"))
            return
        if len(a) != len(b):
            out.append((path, "len", len(a), len(b)))
            return
        for i, (av, bv) in enumerate(zip(a, b)):
            _walk(f"{path}[{i}]", av, bv, out)
    elif isinstance(b, float):
        if not isinstance(a, (int, float)) or abs(a - b) > 1e-6 * max(1, abs(b)):
            out.append((path, "value", a, b))
    else:
        if a != b:
            out.append((path, "value", a, b))


_TAINT_S_FIELDS = {"mom": "mom_s", "gap": "gap_s", "progress": "progress_s", "z": "z_s"}


def _translate_entity(e):
    """Rebuilds the v3-shaped *_s fields (glyph re-applied via the real surfaces function) in place, plus
    the renamed-away fields a brand/overall entity carries in the golden (impact)."""
    for key, field in _TAINT_S_FIELDS.items():
        if field in e:
            e[field] = S.marked(e, key, e[field])
    if e.get("da_s") is not None:
        e["da_s"] = S.marked(e, "da", e["da_s"])
    if "gap_abs_s" in e:
        e["gap_abs_s"] = S.marked(e, "gap", e["gap_abs_s"])
    if "impact_level" in e:
        e["impact"] = S.impact_label(e["impact_level"])
    if "plaus_flags" in e:
        e["plaus"] = S.plaus_message(e["plaus_flags"]) or None


def translate(facts, brand_rename, rename_brands_fn):
    """-> deep copy of facts with every S2-renamed/relocated field reconstructed via the real surfaces.text
    function, so it can be compared field-for-field against the v3 golden (G2: "translate then compare
    exactly"). DECISION_DIVERGENCE paths (clause, collapsed) are left untouched -- the walk skips them.
    C3 (v4.3): also applies the local-only brand-display rename (the golden pre-dates C2's removal of the
    alias registry from committed code)."""
    f = copy.deepcopy(facts)
    cmp_short, cmp_overall, cmp_brand = S.cmp_phrases(f.get("cmp_label"))
    f["cmp_overall"], f["cmp_brand"] = cmp_overall, cmp_brand
    _translate_entity(f["overall"])
    for b in f["brand_order"]:
        e = f["brands"][b]
        _translate_entity(e)
        for ce in e["channels"].values():
            _translate_entity(ce)
    for xe in f.get("channels_x", {}).values():
        _translate_entity(xe)
    for bn in f.get("bottlenecks", []):
        if bn.get("net_gap_tainted"):
            bn["net_gap_abs_s"] = bn["net_gap_abs_s"] + S.WARN
    f["plausibility"] = [{"who": p["who"], "why": S.plaus_message(p["flags"])} for p in f.get("plausibility", [])]
    rename_brands_fn(f, brand_rename)
    return f


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
    facts = translate(r["facts"], V3_RAW_TO_GOLDEN_DISPLAY, rename_brands)

    diffs = []
    _walk("", facts, golden, diffs)
    if diffs:
        msg = "\n".join(f"  {p}: v4={a!r} golden={b!r} ({kind})" for p, kind, a, b in diffs[:50])
        raise AssertionError(f"{len(diffs)} unexplained diffs vs pinned golden:\n{msg}")
    print(f"FULL FACTS PARITY OK (translate-then-compare): 0 unexplained diffs vs output_v3_facts.json "
          f"(ALLOW={len(ALLOW)} entries <= 4 per G2; {len(DECISION_DIVERGENCE)} decision-5 divergences, "
          f"each with its own dedicated test)")


if __name__ == "__main__":
    main()
