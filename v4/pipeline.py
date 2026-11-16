"""Thin orchestrator (S3 of the mid-course structural review): the only module allowed to see both
adapters and facts. detect adapter -> canonical data -> facts -> surfaces. facts.py itself never imports
v4.adapters; this module is where that wiring happens. build() (G3/G8) is the one engine's full entry
point -- the only place the v4 page (via Pyodide) calls for the perf-flash report: no LLM, no
compute.py/layout.py, deterministic end to end (FORBIDDEN: LLM calls in any output)."""
import tomllib
from pathlib import Path

from core import highlight as H
from core import render as R_HTML
from v4 import facts as F
from v4.adapters import registry as R
from v4.adapters.base import Refuse
from v4.surfaces import insights as INSIGHTS
from v4.surfaces import notes as NOTES
from v4.surfaces import text as TEXT

ROOT = Path(__file__).resolve().parent.parent


def _xcheck_report(mism, taint, mom_label):
    """-> warning-panel list [{"col","rows","examples"}]. Ported from the retired compute.py::compute()'s
    own xcheck block: unexplained mismatches only (a z_col row explained by Y, i.e. not in `taint`, is
    excluded). Reporting/diagnostics, not part of facts.compute()'s output (hence excluded from the G2
    full-facts-parity diff -- see test_full_parity.py's ALLOW)."""
    cols = {"progress": "Tiến độ thực tế", "gap": "Vượt / thiếu", "mom": mom_label, "z_col": "Actual vs Plan ngày"}
    out = []
    for k, ms in mism.items():
        rows = [m for m in ms if k != "z_col" or "z" in taint.get((m["b"], m["c"]), ())]
        if rows:
            out.append({"col": cols[k], "rows": len(rows), "examples": [
                f"dòng {m['line']} ({m['b']}/{m['c']}): cột {cols[k]} của bạn {m['mine']} vs tính lại {m['calc']}"
                for m in rows[:3]]})
    return out


def load_typos() -> dict:
    """ROOT/typo_fix.toml [fixes] find->replace, applied to notes text."""
    f = ROOT / "typo_fix.toml"
    return tomllib.loads(f.read_text(encoding="utf-8")).get("fixes", {}) if f.exists() else {}


def _highlight_terms() -> list:
    """templates/perf-flash/highlight_terms.toml's `terms` (domain words like "EOC"/"Run-rate" that
    core.highlight should bold)."""
    f = ROOT / "templates" / "perf-flash" / "highlight_terms.toml"
    return tomllib.loads(f.read_text(encoding="utf-8")).get("terms", []) if f.exists() else []


def _facts_from(order, data, extra, title, timepoint, add, checks, prevs=None):
    """Shared tail of analyze()/combine(): integrity -> crosscheck -> compute -> enrich -> asserts.
    -> (ok, facts_or_None, xcheck_report)."""
    ok = F._integrity(order, data, F.SCHEMA, add, measures=extra.get("integrity_measures", F.LEAF))
    cmp_label = extra.get("cmp_label")
    mom_label = f"GMV vs {cmp_label}" if cmp_label else "So với tháng trước"
    mism, taint = F._crosscheck(order, data, F.SCHEMA, add, mom_label)
    xcheck = _xcheck_report(mism, taint, mom_label)
    if not timepoint.strip():
        add("Mốc thời gian", "fail", "Bắt buộc nhập")
        ok = False
    if not ok:
        return False, None, xcheck
    # cross-check mismatches (mism/taint) are NOT fed into compute()'s taint, by design (ported from the
    # retired compute.py's own comment): they stay warning-panel-only (xcheck), never silently embedded as
    # a ⚠️ in the report itself.
    facts = F.compute(order, data, F.SCHEMA, title, timepoint, extra=extra)
    if prevs:
        F.enrich(facts, prevs, F.SCHEMA, timepoint)
    for a in facts["asserts"]:
        add("Assert: " + a["name"], "ok" if a["ok"] else "fail", a["detail"])
    if not all(a["ok"] for a in facts["asserts"]):
        return False, None, xcheck
    facts["checks"] = checks
    return True, facts, xcheck


def analyze(text, title="", timepoint="", prevs=None):
    """-> {"ok", "checks", "summary", "facts", "suggest"} (facts only when ok). `prevs`: saved payloads of
    the same campaign (newest first) for stale-column/delta enrichment -- loading them from disk is the
    caller's job (orchestrator-level I/O), not pipeline.py's or facts.py's."""
    checks = []

    def add(name, status, detail="", row=None):
        checks.append({"name": name, "status": status, "detail": detail, "row": row})

    base = {"ok": False, "checks": checks, "summary": {}, "facts": None, "suggest": None}
    try:
        fmt, order, data, extra = R.parse(text, add)
    except Refuse as e:
        add("Input", "fail", e.reason, row=None)
        return base
    base["suggest"] = extra.get("suggest")
    base["summary"] = {"rows": sum(len(data[b]) for b in order), "brands": order}
    ok, facts, xcheck = _facts_from(order, data, extra, title, timepoint, add, checks, prevs=prevs)
    base["xcheck"] = xcheck
    if not ok:
        return base
    base.update(ok=True, facts=facts)
    base["summary"]["total_actual"] = facts["overall"]["actual_s"]
    base["summary"]["net_gap"] = facts["overall"]["gap_s"]
    return base


def combine(blocks_text: list, title="", timepoint="", prevs=None):
    """-> same shape as analyze(). Decision 3 (multi-platform): `blocks_text` is one pasted block PER
    PLATFORM (the caller splits -- the web UI pastes each platform separately, see web/v4/index.html; a
    CLI/test caller passes a list directly). Brand totals are SUMMED across platforms for the text report
    (R5, CHARTER v4.4: charts removed, so the per-platform split itself is no longer kept as a fact --
    nothing reads it; only the combined totals and `caps.has_platforms` survive). Refuses (never guesses/
    averages) when platforms disagree on run-rate or comparison period -- G5."""
    checks = []

    def add(name, status, detail="", row=None):
        checks.append({"name": name, "status": status, "detail": detail, "row": row})

    base = {"ok": False, "checks": checks, "summary": {}, "facts": None, "suggest": None}
    if len(blocks_text) == 1:
        return analyze(blocks_text[0], title, timepoint, prevs=prevs)
    parsed = []
    for i, text in enumerate(blocks_text, 1):
        try:
            fmt, order, data, extra = R.parse(text, add)
        except Refuse as e:
            add(f"Input (block {i})", "fail", e.reason, row=None)
            return base
        parsed.append((order, data, extra))
    tot = F.SCHEMA["channels"]["total"]
    run_rates = []
    for order, data, extra in parsed:
        plan = sum(data[b][tot]["plan"] for b in order)
        ptd = sum(data[b][tot]["ptd"] for b in order)
        run_rates.append(ptd / plan if plan else None)
    tol = F.SCHEMA["checks"].get("v3_runrate_tol_pp", 0.01) / 100
    if any(rr is None for rr in run_rates) or max(run_rates) - min(run_rates) > tol:
        add("Run-rate giữa các platform", "fail",
            "Run-rate khác nhau giữa các block platform ({}) -- không tự gộp, cần xác nhận lại input"
            .format(", ".join(f"{rr:.2%}" if rr is not None else "?" for rr in run_rates)))
        return base
    cmp_labels = {extra.get("cmp_label") for _, _, extra in parsed if extra.get("cmp_label")}
    if len(cmp_labels) > 1:
        add("Kỳ so sánh giữa các platform", "fail",
            "Các block platform có kỳ so sánh khác nhau (" + ", ".join(sorted(cmp_labels)) + ") -- không tự gộp")
        return base
    combined_order, combined_data = [], {}
    platform_names = set()
    for order, data, extra in parsed:
        platform_names.add(extra.get("platform") or "?")
        for b in order:
            if b not in combined_data:
                combined_data[b] = {}
                combined_order.append(b)
            for c, d in data[b].items():
                cd = combined_data[b].setdefault(c, {"plan": 0, "ptd": 0, "actual": 0, "last": 0,
                                                      "line": d["line"], "x": {}})
                for k in ("plan", "ptd", "actual", "last"):
                    cd[k] += d[k]
    merged_extra = dict(parsed[0][2])
    merged_extra["platform"] = " + ".join(sorted(platform_names))
    merged_extra["caps"] = dict(merged_extra.get("caps", {}))
    merged_extra["caps"]["has_platforms"] = True
    base["summary"] = {"rows": sum(len(combined_data[b]) for b in combined_order), "brands": combined_order}
    ok, facts, xcheck = _facts_from(combined_order, combined_data, merged_extra, title, timepoint, add, checks, prevs=prevs)
    base["xcheck"] = xcheck
    if not ok:
        return base
    base.update(ok=True, facts=facts)
    base["summary"]["total_actual"] = facts["overall"]["actual_s"]
    base["summary"]["net_gap"] = facts["overall"]["gap_s"]
    return base


def _finish(r, title, notes_raw):
    """Shared tail of build()/build_multi(): notes.attach() -> surfaces.text.render() -> core.render
    (md/text/HTML) -> insights -> warnings. `r` is an already-ok analyze()/combine() result."""
    facts = r["facts"]
    notes = NOTES.attach(notes_raw, facts["brand_order"], load_typos())
    blocks = TEXT.render(facts, notes)
    # core.highlight is a shared, non-compute formatting pass (money/signed-number/brand-name bolding) that
    # the retired engine also ran via core.pipeline._build()'s finalize() -- ported here so v4's rendered
    # text keeps the same bold-markup fidelity, not just the same numbers (G8: Lark bold). C2: brand_order
    # is the brands AS PASTED this run -- no committed alias list to add here.
    words = list(facts["brand_order"]) + _highlight_terms()
    scope = F.SCHEMA.get("display", {}).get("marker_scope", "headline")
    blocks = [{**b, "s": H.highlight(b["s"], words, scope)} for b in blocks]
    r["notes"] = notes
    r["blocks"] = blocks
    r["insights"] = INSIGHTS.generate(facts)
    r["out"] = {"md": R_HTML.to_md(blocks, "md"), "text": R_HTML.to_text(blocks),
                "html_msg": R_HTML.to_html(blocks, "msg"), "html_doc": R_HTML.to_html(blocks, "doc")}
    r["warnings"] = {
        # no LLM in this engine (decision 4/5, FORBIDDEN) -- every LLM-only warning field is a fixed empty/
        # zero default, kept only so the existing web/index.html warning-bar JS (which reads these keys
        # unconditionally) doesn't need a v4-specific code path.
        "missing": sum(b["s"].count(TEXT.MISSING) for b in blocks), "retries": 0, "retries_binding": 0,
        "retries_fixed": 0, "misattributed": [], "typos_fixed": 0, "unverified": [], "fallbacks": [],
        "banned": [], "rules_failed": [], "prefix_stripped": [], "digits_outside": [],
        "tp_stale": bool(facts.get("tp_stale")),
        "stale_cols": [{**sc, "text": TEXT.stale_col_message(sc)} for sc in facts.get("stale_cols", [])],
        "xcheck": r.get("xcheck", []),
        "plausibility": [{"who": p["who"], "why": TEXT.plaus_message(p["flags"])} for p in facts.get("plausibility", [])],
        "notes_unmatched": notes["unmatched"],
        "checks_warn": [c["name"] + ": " + c["detail"] for c in r["checks"] if c["status"] == "warn"],
        "llm": False,
    }
    return r


def build(text, title="", timepoint="", notes_raw="", prevs=None):
    """-> {"ok", "checks", "facts", "notes", "blocks", "out": {md,text,html_msg,html_doc}, "warnings",
    "insights"} when ok else {"ok": False, "checks": [...]}. The full deterministic report for a
    SINGLE pasted block: analyze() -> _finish(). No LLM anywhere (decision 4/5, FORBIDDEN). G6: unattached
    note lines are never dropped -- they ride along in notes["unmatched"] AND warnings["notes_unmatched"]
    for the caller/web UI to warn on and block Copy until acknowledged."""
    r = analyze(text, title, timepoint, prevs=prevs)
    if not r["ok"]:
        return r
    return _finish(r, title, notes_raw)


def build_multi(blocks_text: list, title="", timepoint="", notes_raw="", prevs=None):
    """Same as build(), for MULTIPLE pasted platform blocks (decision 3) -- combine() instead of analyze()
    for the facts, otherwise identical tail (notes/render/insights/warnings)."""
    r = combine(blocks_text, title, timepoint, prevs=prevs)
    if not r["ok"]:
        return r
    return _finish(r, title, notes_raw)
