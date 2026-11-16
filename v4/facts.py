"""FACTS layer (decision 1 of CHARTER v4): computed once from canonical adapter-normalized rows. Holds
numbers, formatted number strings (single rounding source via core.numfmt) and capability/structural flags
only -- NO Vietnamese wording (S2 of the mid-course review). Sentences ("vuot/hut", "base nho", "vs plan
ngay", impact labels, plausibility messages, comparison-period phrasing) are assembled by SURFACES
(v4/surfaces/text.py) from these flags, never computed or re-rounded here.

Taint markers (checkpoint judgment call 1, after S2): a formatted number string never carries the ⚠️ glyph
itself. Each entity dict carries `tainted` (list of keys: "mom"/"gap"/"progress"/"z") and, where relevant,
a `da_bad` bool; SURFACES decides the marker glyph and which channel (Messenger/Docs) gets it.

Direction (S3): this module takes CANONICAL DATA ONLY -- {brand: {channel: {plan, ptd, actual, last, line,
x}}} rows an adapter already produced, plus adapter metadata (`extra`: cmp_label, caps, grand_total,
k_values, platform). It never imports v4.adapters and never reads raw pasted text; the orchestrator
(v4/pipeline.py) is what wires adapter -> facts -> surfaces together.

One concept, one formula: run-rate = ptd/plan; progress = actual/plan; Y = progress - run-rate; Z =
actual/ptd - 1; gap = actual - ptd; growth = actual/last - 1; EOC = actual/run-rate; contribution = plan/
total plan. This is the ONLY place these formulas are defined (S1) -- templates/perf-flash/compute.py's own
copy is retired (see its module docstring) once the local server is cut over to this package.
"""
from fractions import Fraction
from pathlib import Path
import tomllib

from core import numfmt as N

LEAF = ("plan", "ptd", "actual", "last")

_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "templates" / "perf-flash" / "schema.toml"
SCHEMA = tomllib.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))

# contribution -> structural tier; SURFACES maps this to Vietnamese text ("anh huong lon/trung binh/nho").
IMPACT_HIGH, IMPACT_MID, IMPACT_LOW = "high", "mid", "low"


def _impact_level(contrib, S):
    t = S["thresholds"]
    return IMPACT_HIGH if contrib >= t["contribution_high"] else IMPACT_MID if contrib >= t["contribution_mid"] else IMPACT_LOW


def _dn(S, c):
    """Channel display-name lookup (config data from schema.toml, not generated prose) -- shared by facts'
    own bottleneck labels and by surfaces; kept here since it is a straight config lookup, not wording."""
    return S.get("channel_display", {}).get(c, c)


def _plaus_flags(plan, last, mom, S):
    """-> list of structured threshold-breach records (no Vietnamese text; SURFACES renders the message)."""
    p = S.get("plausibility", {})
    out = []
    if mom is not None and abs(mom) > p.get("max_abs_mom", 0.8):
        out.append({"check": "max_abs_mom", "value": mom, "threshold": p.get("max_abs_mom", 0.8)})
    if plan and last > p.get("max_last_vs_plan", 1.5) * plan:
        out.append({"check": "max_last_vs_plan", "last": last, "plan": plan, "threshold": p.get("max_last_vs_plan", 1.5)})
    return out


def _ent(plan, ptd, actual, last, S, level, bad=(), has_comparison=False):
    d = S["display"]
    nd = d["overall_pct_decimals"] if level == "overall" else d["brand_pct_decimals"]
    rr = Fraction(ptd, plan) if plan else None
    progress = Fraction(actual, plan) if plan else None
    y = progress - rr if rr is not None else None
    z = Fraction(actual, ptd) - 1 if ptd else None
    gap = actual - ptd
    mom = Fraction(actual, last) - 1 if last else None
    eoc = N.rnd(Fraction(actual) / rr) if rr else None
    eoc_ratio = Fraction(eoc, plan) if eoc is not None and plan else None
    eoc_gap = eoc - plan if eoc is not None else None
    money = N.full if level == "overall" else (lambda n, signed=False: N.short(
        n, signed, d["m_decimals"], d["b_decimals"], d["k_decimals"]))
    dash = "—"
    e = {
        "plan": plan, "ptd": ptd, "actual": actual, "last": last, "gap": gap, "eoc": eoc, "eoc_gap": eoc_gap,
        "run_rate": float(rr) if rr is not None else None,
        "progress": float(progress) if progress is not None else None,
        "y_pp": float(y * 100) if y is not None else None,
        "z": float(z) if z is not None else None,
        "mom": float(mom) if mom is not None else None,
        "eoc_pct": float(eoc_ratio) if eoc_ratio is not None else None,
        "plan_s": money(plan), "ptd_s": money(ptd), "actual_s": money(actual), "last_s": money(last),
        "gap_s": money(gap, True), "gap_abs_s": money(abs(gap)),
        "eoc_s": money(eoc) if eoc is not None else dash,
        "eoc_gap_abs_s": money(abs(eoc_gap)) if eoc_gap is not None else dash,
        "run_rate_s": N.pct(rr, d["overall_pct_decimals"]) if rr is not None else dash,
        "progress_s": N.pct(progress, nd) if progress is not None else dash,
        "y_s": N.pct(y, nd, True, "pp") if y is not None else dash,
        "z_s": N.pct(z, nd, True) if z is not None else dash,
        "mom_s": N.pct(mom, nd, True) if mom is not None else dash,
        "eoc_pct_s": N.pct(eoc_ratio, d["eoc_pct_decimals"]) if eoc_ratio is not None else dash,
    }
    if level == "overall":
        e["eoc_b_s"] = N.short_b1(eoc) if eoc is not None else dash
        e["gap_abs_short_s"] = N.short(abs(gap))
        # decision 5c: full VND digits only on the Target line; every other overall VND figure in the
        # rendered report uses the short/abbreviated form (surfaces' choice of which _s field to print).
        sh = lambda n, signed=False: N.short(n, signed, d["m_decimals"], d["b_decimals"], d["k_decimals"])  # noqa: E731
        e["plan_sh"], e["ptd_sh"], e["actual_sh"] = sh(plan), sh(ptd), sh(actual)
        e["gap_sh"], e["gap_abs_sh"] = sh(gap, True), sh(abs(gap))
        e["eoc_sh"] = sh(eoc) if eoc is not None else dash
        e["eoc_gap_abs_sh"] = sh(abs(eoc_gap)) if eoc_gap is not None else dash
    rem, prem = plan - actual, plan - ptd
    pace = Fraction(rem, prem) if prem > 0 and rem > 0 else None
    e["req_rem"] = max(rem, 0)
    e["req_rem_s"] = money(max(rem, 0))
    if level == "overall":
        e["req_rem_sh"] = N.short(max(rem, 0), False, d["m_decimals"], d["b_decimals"], d["k_decimals"])
    e["req_pace"] = float(pace) if pace is not None else None
    e["req_pace_s"] = N.pct(pace, 1) if pace is not None else dash
    e["rest_s"] = N.pct(1 - rr, d["overall_pct_decimals"]) if rr is not None else dash
    e["hard"] = bool(pace is not None and pace > Fraction(str(S.get("enrich", {}).get("hard_pace", 2.0))))
    e["small"] = ptd < S["thresholds"]["min_plan_to_date"]
    # has_comparison inputs (v3-style DA) skip the raw-MoM plausibility guard: tuned for steady-state MoM,
    # false-positives on normal campaign-day swings. Anomalies there are tagged by the adapter instead (da_bad).
    e["plaus_flags"] = [] if has_comparison else _plaus_flags(plan, last, e["mom"], S)
    bad = set(bad) | ({"mom"} if e["plaus_flags"] and e["mom"] is not None and not e["small"] else set())
    e["tainted"] = sorted(bad)
    return e


def _integrity(order, data, S, add, measures=LEAF):
    """Cross-row assert: Affiliate + Self-sell = TOTAL, LIVE+Video+Showcase = Self-sell. Canonical-data-only
    (operates on adapter-normalized rows), format-agnostic -- lives in FACTS per decision 1 ("all asserts
    here"), not in any one adapter.

    R2 (CHARTER v4.4): `measures` lets the caller restrict this to the columns that were actually PASTED,
    never a derived one. v2's "plan" is a real pasted column (checked). v3 has no Plan column at all --
    "plan" there is DERIVED (plan_to_date / % Required) and re-asserting it just amplifies the source
    paste's own ±1 VND rounding past tolerance on every arithmetic combination of the derivation; v3's
    adapter passes `extra["integrity_measures"]` (ptd/actual/last only) to exclude it."""
    ch, tol = S["channels"], S["checks"]["tolerance_vnd"]
    ok = True
    for b in order:
        for m in measures:
            T_ = data[b][ch["total"]][m]
            a, s = data[b][ch["affiliate"]][m], data[b][ch["self_sell"]][m]
            if abs(a + s - T_) > tol:
                ok = False
                add("Affiliate + Self-sell = TOTAL", "fail",
                    f"{b}: {a:,} + {s:,} = {a + s:,} ≠ TOTAL {T_:,} (lệch {a + s - T_:,})")
            kids = sum(data[b][c][m] for c in ch["self_children"])
            if abs(kids - s) > tol:
                ok = False
                add("LIVE + Video + Showcase = Self-sell", "fail",
                    f"{b}: tổng 3 kênh con {kids:,} ≠ Self-sell {s:,} (lệch {kids - s:,})")
    if ok:
        add("Affiliate + Self-sell = TOTAL", "ok", f"{len(order)} brand × {len(measures)} thước đo, sai số ≤ {tol} VNĐ")
        add("LIVE + Video + Showcase = Self-sell", "ok", f"{len(order)} brand × {len(measures)} thước đo, sai số ≤ {tol} VNĐ")
    return ok


def _crosscheck(order, data, S, add, mom_label):
    """Cross-check adapter-supplied precomputed columns (progress/gap/mom/z_col) against facts' own
    recomputed values. Canonical-data-only, format-agnostic."""
    mism, taint = {"progress": [], "gap": [], "mom": [], "z_col": []}, {}
    z_is_y = 0
    min_ptd = S["thresholds"]["min_plan_to_date"]
    rel = S["checks"].get("xcheck_rel_tol", 5e-4)
    off = lambda a, b, tol: abs(a - b) > max(tol, rel * abs(b))  # noqa: E731

    def hit(k, b, c, d, mine, calc, metric):
        mism[k].append({"b": b, "c": c, "line": d["line"], "mine": mine, "calc": calc})
        if metric:
            taint.setdefault((b, c), set()).add(metric)

    for b in order:
        for c, d in data[b].items():
            x, plan, ptd, act, last = d["x"], d["plan"], d["ptd"], d["actual"], d["last"]
            if ptd < min_ptd:
                continue
            if x.get("progress") is not None and off(act / plan * 100, x["progress"], 0.011):
                hit("progress", b, c, d, f"{x['progress']:+.2f}%", f"{act / plan * 100:+.2f}%", "progress")
            if x.get("gap") is not None and abs((act - ptd) - x["gap"]) > 1:
                hit("gap", b, c, d, f"{x['gap']:,}", f"{act - ptd:,}", "gap")
            if x.get("mom") is not None and last and off((act / last - 1) * 100, x["mom"], 0.011):
                hit("mom", b, c, d, f"{x['mom']:+.2f}%", f"{(act / last - 1) * 100:+.2f}%", "mom")
            if x.get("z_col") is not None and ptd and plan:
                z = (act / ptd - 1) * 100
                y = (act / plan - ptd / plan) * 100
                if off(z, x["z_col"], 0.011):
                    explained = not off(y, x["z_col"], 0.011)
                    z_is_y += explained
                    hit("z_col", b, c, d, f"{x['z_col']:+.2f}%", f"{z:+.2f}%", None if explained else "z")
    present = {k for b in order for d in data[b].values() for k in d["x"]}
    for k, label in (("progress", "Tiến độ thực tế"), ("gap", "Vượt / thiếu"), ("mom", mom_label)):
        if k in present:
            add(f"Đối soát cột '{label}'", "warn" if mism[k] else "ok",
                f"{len(mism[k])} dòng lệch số tính lại" if mism[k] else "khớp số tính lại")
    if "z_col" in present:
        n = len(mism["z_col"])
        add("Đối soát cột 'Actual vs Plan ngày'", "warn" if n else "ok",
            f"{n} dòng lệch Z tính lại ({z_is_y}/{n} khớp Y)" if n else "khớp Z tính lại")
    return mism, taint


def compute(order, data, S, title, timepoint="", taint=None, extra=None):
    """-> facts dict. CANONICAL DATA ONLY (S3): `data`/`order` are adapter-normalized rows, `extra` is
    adapter metadata (cmp_label, caps, grand_total, k_values, platform) -- plain data, not adapter code.
    No Vietnamese wording is produced here (S2): no clause/impact text, no comparison-period phrasing --
    only cmp_label (the raw label string) and structural flags are returned for SURFACES to render."""
    extra = extra or {}
    caps = extra.get("caps", {"has_comparison": False, "has_da": False, "has_channels": True, "has_platforms": False})
    cmp_label = extra.get("cmp_label")
    ch = S["channels"]
    tot = ch["total"]
    taint = taint or {}
    tk = lambda cells: set().union(*[taint.get(k, set()) for k in cells])  # noqa: E731
    has_comparison = caps.get("has_comparison", False)

    def da_of(row_x):
        if not caps.get("has_da") or row_x.get("da") is None:
            return None, None, False
        return row_x["da"], f"{row_x['da']:+.1f}%", bool(row_x.get("da_bad"))

    sums = {m: sum(data[b][tot][m] for b in order) for m in LEAF}
    overall = _ent(sums["plan"], sums["ptd"], sums["actual"], sums["last"], S, "overall",
                   tk((b, tot) for b in order), has_comparison=has_comparison)
    net_gap = overall["gap"]
    msh = Fraction(str(S["thresholds"]["material_share"]))
    brands = {}
    for b in order:
        d = data[b]
        e = _ent(d[tot]["plan"], d[tot]["ptd"], d[tot]["actual"], d[tot]["last"], S, "brand", tk([(b, tot)]),
                 has_comparison=has_comparison)
        e["da_pct"], e["da_s"], e["da_bad"] = da_of(d[tot]["x"])
        contrib = Fraction(d[tot]["plan"], sums["plan"])
        e["contribution"] = float(contrib)
        e["contribution_s"] = N.pct(contrib, 1)
        e["impact_level"] = _impact_level(contrib, S)
        e["kind"] = "highlight" if e["gap"] >= 0 else "lowlight"
        # S1 (CHARTER v4.6, Hiếu's decision): small = plan share AND actual share both below threshold --
        # a brand that has grown past the threshold on actual (even with a stale/low plan share) stays a
        # full block. Was plan-share-only (decision 5e, v4.1 charter); same threshold key/value, same
        # "either kind" collapse. Both shares are exposed on every brand regardless of collapse outcome.
        plan_share = contrib
        actual_share = Fraction(d[tot]["actual"], sums["actual"])
        e["plan_share"] = float(plan_share)
        e["plan_share_s"] = N.pct(plan_share, 1)
        e["actual_share"] = float(actual_share)
        e["actual_share_s"] = N.pct(actual_share, 1)
        sbs = S["display"].get("small_brand_share_v4", S["display"].get("small_brand_share", 0))
        e["collapsed"] = bool(sbs) and plan_share < Fraction(str(sbs)) and actual_share < Fraction(str(sbs))
        e["channels"] = {}
        for c in [ch["affiliate"], ch["self_sell"], *ch["self_children"]]:
            x = d[c]
            ce = _ent(x["plan"], x["ptd"], x["actual"], x["last"], S, "brand", tk([(b, c)]), has_comparison=has_comparison)
            ce["base_nho"] = bool(x["x"].get("base_nho"))
            ce["da_pct"], ce["da_s"], ce["da_bad"] = da_of(x["x"])
            e["channels"][c] = ce
        pool = [(c, e["channels"][c]) for c in ch["pick_from"]
                if not e["channels"][c]["small"] and abs(e["channels"][c]["gap"]) >= msh * abs(e["gap"])]
        e["pos"] = [p[0] for p in sorted([p for p in pool if p[1]["gap"] > 0], key=lambda p: -p[1]["gap"])]
        e["neg"] = [p[0] for p in sorted([p for p in pool if p[1]["gap"] < 0], key=lambda p: p[1]["gap"])]
        brands[b] = e
    xch, asserts = {}, []
    for c in [ch["affiliate"], ch["self_sell"], *ch["self_children"]]:
        agg = {m: sum(data[b][c][m] for b in order) for m in LEAF}
        a = _ent(agg["plan"], agg["ptd"], agg["actual"], agg["last"], S, "brand", tk((b, c) for b in order),
                 has_comparison=has_comparison)
        a["per_brand"] = {b: brands[b]["channels"][c]["gap"] for b in order}
        xch[c] = a
    tol = S["checks"]["tolerance_vnd"] * len(order)
    s1 = xch[ch["affiliate"]]["gap"] + xch[ch["self_sell"]]["gap"]
    s2 = sum(xch[c]["gap"] for c in ch["self_children"])
    asserts.append({"name": "Σ gap Affiliate + Self-sell = gap ròng", "ok": abs(s1 - net_gap) <= tol,
                    "detail": f"{s1:,} vs {net_gap:,}"})
    asserts.append({"name": "Σ gap LIVE + Video + Showcase = gap Self-sell", "ok": abs(s2 - xch[ch["self_sell"]]["gap"]) <= tol,
                    "detail": f"{s2:,} vs {xch[ch['self_sell']]['gap']:,}"})
    asserts.append({"name": "Σ gap brand TOTAL = gap ròng", "ok": sum(brands[b]["gap"] for b in order) == net_gap,
                    "detail": f"{sum(brands[b]['gap'] for b in order):,} vs {net_gap:,}"})
    bottlenecks = []
    if net_gap < 0:
        for c in ch["pick_from"]:
            if c not in xch:
                continue
            g = xch[c]["gap"]
            share = Fraction(g, net_gap) if g < 0 else Fraction(0)
            if g < 0 and share >= Fraction(str(S["thresholds"]["bottleneck_share"])):
                per = sorted([(b, brands[b]["channels"][c]) for b in order
                              if brands[b]["channels"][c]["gap"] < 0 and not brands[b]["channels"][c]["small"]
                              and abs(brands[b]["channels"][c]["gap"]) >= msh * abs(g)],
                             key=lambda p: p[1]["gap"])
                bottlenecks.append({
                    "channel": c, "channel_d": _dn(S, c), "gap": g, "gap_s": xch[c]["gap_s"], "gap_abs_s": xch[c]["gap_abs_s"],
                    "share": float(share), "share_s": N.pct(share, 1), "net_gap_abs_s": N.short(abs(net_gap)),
                    "net_gap_tainted": "gap" in overall["tainted"], "z_s": xch[c]["z_s"],
                    "per_brand": [{"brand": b, "gap_s": e["gap_s"], "gap_abs_s": e["gap_abs_s"]} for b, e in per],
                })
        bottlenecks.sort(key=lambda x: x["gap"])
    cell_bottlenecks = []
    if has_comparison:
        ptd10 = Fraction(1, 10) * sums["ptd"]
        for b in order:
            for c in ch["pick_from"]:
                ce = brands[b]["channels"][c]
                if ce["gap"] < 0 and (abs(ce["gap"]) > abs(net_gap) or abs(ce["gap"]) >= ptd10):
                    ratio_s = f"{abs(ce['gap']) / abs(net_gap):.1f}" if net_gap else None
                    cell_bottlenecks.append({"brand": b, "channel": c, "channel_d": _dn(S, c), "gap": ce["gap"],
                                             "gap_s": ce["gap_s"], "gap_abs_s": ce["gap_abs_s"], "ratio_s": ratio_s,
                                             "net_gap_s": N.short(net_gap, True)})
        cell_bottlenecks.sort(key=lambda x: x["gap"])
    plaus = [{"who": who, "flags": e["plaus_flags"]} for who, e in
             [("Overall", overall)] + [(f"{b}/TOTAL", brands[b]) for b in order]
             + [(f"{b}/{c}", brands[b]["channels"][c]) for b in order for c in brands[b]["channels"]
                if not brands[b]["channels"][c]["small"]] if e["plaus_flags"]]
    facts = {
        "title": title.strip() or "[TEN KENH/SAN - GIAI DOAN/CHIEN DICH]",
        "timepoint": timepoint.strip(),
        "enrich": dict(S.get("enrich", {})),
        "overall": overall, "brands": brands, "brand_order": order,
        "highlights": sorted([b for b in order if brands[b]["kind"] == "highlight"], key=lambda b: -brands[b]["gap"]),
        "lowlights": sorted([b for b in order if brands[b]["kind"] == "lowlight"], key=lambda b: brands[b]["gap"]),
        "channels_x": xch, "bottlenecks": bottlenecks, "cell_bottlenecks": cell_bottlenecks, "asserts": asserts,
        "plausibility": plaus,
        "disp": {c: _dn(S, c) for c in S["channels"]["pick_from"]},
        "cmp_label": cmp_label,  # raw label only; "so voi <cmp_label>" / "vs <cmp_label>" phrasing is SURFACES' job
        "caps": caps, "platform": extra.get("platform"),
        "rows": {f"{b}|{c}": {"x": data[b][c]["x"], "raw": [data[b][c]["plan"], data[b][c]["ptd"],
                 data[b][c]["actual"], data[b][c]["last"]]} for b in order for c in data[b]},
        "stale_cols": [], "tp_stale": False, "delta": None,  # filled by enrich() when prev runs are available
    }
    if has_comparison:
        gt_x = (extra.get("grand_total") or {}).get("x") or {}
        da = gt_x.get("da")
        facts["overall"]["da_pct"] = da
        facts["overall"]["da_s"] = f"{da:+.1f}%" if da is not None else None
        facts["overall"]["da_bad"] = bool(gt_x.get("da_bad"))
        ks = extra.get("k_values") or []
        facts["da_k"] = {"k": round(sum(ks) / len(ks), 4), "n": len(ks), "min": round(min(ks), 4),
                         "max": round(max(ks), 4)} if ks else None
    return facts


# ---------- enrichments that need the previous saved run(s) ----------
# col key -> display label (config data, like _dn -- not a generated sentence). Ported from the retired
# templates/perf-flash/compute.py::enrich()/_COLS; ported here as part of allowlist discipline (checkpoint
# review: rows/stale_cols/tp_stale/delta must be ported into v4, not left as permanent ALLOW exceptions).
_COLS = {"progress": "Tiến độ thực tế", "gap": "Vượt / thiếu", "z_col": "Actual vs Plan ngày", "mom": "So với tháng trước"}


def enrich(facts, prevs, S, timepoint):
    """prevs: saved payloads of the same campaign (orchestrator's job to load them), newest first. Sets
    facts["stale_cols"] (structural: col/same/of/prev counts, no Vietnamese sentence -- SURFACES renders the
    message), facts["tp_stale"] (bool) and facts["delta"] (numeric/formatted-string only, no sentence)."""
    facts["stale_cols"], facts["tp_stale"], facts["delta"] = [], False, None
    tp = timepoint.strip().casefold()
    rr = facts["overall"]["run_rate"]
    for p in prevs:
        if (p.get("timepoint") or "").strip().casefold() == tp:
            r0 = ((p.get("facts") or {}).get("overall") or {}).get("run_rate")
            facts["tp_stale"] = r0 is not None and abs(r0 - rr) > 1e-6
            break
    prev = next((p for p in prevs if (p.get("timepoint") or "").strip().casefold() != tp and p.get("facts")), None)
    if not prev:
        return facts
    ptp, pf = prev.get("timepoint") or "", prev["facts"]
    C, min_ptd = S["checks"], S["thresholds"]["min_plan_to_date"]
    old, new = pf.get("rows") or {}, facts["rows"]
    for k, label in _COLS.items():
        comp = same = 0
        for key, cur in new.items():
            o = old.get(key)
            if not o or cur["raw"][1] < min_ptd or o["raw"][1] < min_ptd:
                continue
            a, b = cur["x"].get(k), o["x"].get(k)
            if a is None or b is None or cur["raw"][2] == o["raw"][2]:
                continue
            comp += 1
            same += abs(a - b) < 1e-9
        if comp >= C.get("stale_min_rows", 5) and same / comp >= C.get("stale_share", 0.6):
            facts["stale_cols"].append({"col": label, "same": same, "of": comp, "prev": ptp})
    if not S.get("enrich", {}).get("delta", True):
        return facts
    mn = Fraction(str(S.get("enrich", {}).get("delta_min_pp", 0.1)))
    zo, zn = (pf.get("overall") or {}).get("z"), facts["overall"]["z"]
    if zo is None or zn is None:
        return facts
    d = {"prev_tp": ptp, "z_old_s": pf["overall"]["z_s"], "z_new_s": facts["overall"]["z_s"],
         "eoc_old_s": pf["overall"]["eoc_pct_s"], "eoc_new_s": facts["overall"]["eoc_pct_s"], "better": [], "worse": []}
    rows = []
    for b in facts["brand_order"]:
        o = (pf.get("brands") or {}).get(b)
        if o and o.get("z") is not None and facts["brands"][b]["z"] is not None:
            diff = Fraction(facts["brands"][b]["z"]) - Fraction(o["z"])
            if abs(diff * 100) >= mn:
                rows.append((diff, b))
    for diff, b in sorted(rows, key=lambda r: -abs(r[0])):
        (d["better"] if diff > 0 else d["worse"]).append({"brand": b, "pp_s": N.pct(diff, 1, True, "pp")})
    facts["delta"] = d
    return facts
