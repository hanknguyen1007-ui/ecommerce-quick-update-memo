"""Text surface (decision 1: SURFACES only select and format FACTS, never compute). This module holds the
Vietnamese wording moved out of facts.py per the mid-course structural review (S2): channel clauses,
impact-level labels, plausibility messages, comparison-period phrasing and the ⚠️ taint marker. It does not
recompute or re-round any number -- every figure it prints is a *_s string, or a raw float formatted here
with core.numfmt (the same single rounding source facts.py itself uses), already produced by facts.compute().

render(facts, notes) is the full decision-5 report renderer (v4.1 charter), ported from the retired
templates/perf-flash/layout.py with the five wording changes:
  5a hide "Fact vận hành" entirely when a highlight brand has no notes (no [cần bổ sung] placeholder)
  5b "{vượt/hụt} plan ngày {Z%}" phrasing (was "{Z%} vs plan ngày" + a separate gap bullet)
  5c full VND digits only on the Target line; every other Overall VND figure uses the short/abbreviated form
  5d base-nhỏ channel bullets use the SAME shape as a normal bullet, just with a "(base nhỏ)" tag on the Z bit
  5e brands below the plan-share threshold collapse into a "Nhóm brand nhỏ" block regardless of
     highlight/lowlight kind (was lowlight-only, 1% threshold; now 2%, config key small_brand_share_v4)

CHARTER v4.2 fixes on top of decision 5:
  H2 "Nhóm brand nhỏ" is its OWN section, placed after Lowlights, ALWAYS (never folded into Highlights,
     even when every collapsed brand happens to be positive that run -- one rule, stated once, no run-time
     branching on the mix of signs). One full bullet per brand: actual · {vượt/hụt} plan ngày Z% · gap ·
     Forecast EOC%, each signed figure getting the same 🟢/🔴 marker highlights/lowlights headlines use.
  H3 no double negatives: when a word already carries the direction (vượt/hụt), the number next to it is
     UNSIGNED (e.g. "hụt plan ngày 33.0%", never "hụt plan ngày -33.0%"). Applied everywhere a vượt/hụt
     word and a signed % sit next to each other: clause()'s Z bit and the Overall "Vượt/Hụt plan ngày" line.
"""
from core import numfmt as N

WARN = "⚠️"
MISSING = "[cần bổ sung]"
NONE_MATERIAL = "chưa có kênh vượt ngưỡng trọng yếu."


def marked(e: dict, key: str, field_s: str) -> str:
    """Appends the taint glyph to a formatted number string when facts flagged that logical field tainted
    (checkpoint judgment call 1: facts never embeds the glyph itself -- it only carries e['tainted'] /
    e['da_bad']; SURFACES decides the marker here). `key` is one of facts' tainted-list keys ("mom"/"gap"/
    "progress"/"z") or "da" (uses e['da_bad'] instead)."""
    bad = e.get("da_bad") if key == "da" else key in e.get("tainted", ())
    return field_s + WARN if bad else field_s


IMPACT_LABEL = {"high": "ảnh hưởng lớn", "mid": "ảnh hưởng trung bình", "low": "ảnh hưởng nhỏ"}


def impact_label(level: str) -> str:
    return IMPACT_LABEL.get(level, level)


def cmp_phrases(cmp_label):
    """-> (cmp_short, cmp_overall, cmp_brand). cmp_label is the raw string from facts (e.g. 'Tháng 10/2026'),
    or None for v2-style inputs with no named comparison period (falls back to MoM phrasing). Ported verbatim
    from the retired compute.py::compute()'s cmp_short/cmp_overall/cmp_brand locals."""
    if cmp_label:
        return f"vs {cmp_label}", f"so với {cmp_label}", f"vs {cmp_label}"
    return "MoM", "so với cùng kỳ tháng trước", "vs tháng trước"


def plaus_message(flags: list) -> str:
    """flags: facts' e['plaus_flags'] (list of structured breach records, no text). -> Vietnamese message,
    or '' when empty. Ported verbatim from the retired facts._plaus's per-reason f-strings."""
    bits = []
    for f in flags:
        if f["check"] == "max_abs_mom":
            bits.append(f"|MoM| {N.pct(f['value'], 1, True)} > {f['threshold']:.0%}")
        elif f["check"] == "max_last_vs_plan":
            bits.append(f"Actual tháng trước {N.short(f['last'])} > {f['threshold']}× Plan {N.short(f['plan'])}")
    return "; ".join(bits)


def stale_col_message(sc: dict) -> str:
    """sc: one of facts['stale_cols'] entries (col/same/of/prev, no text). -> Vietnamese sentence. Ported
    from the retired templates/perf-flash/compute.py::enrich()'s inline f-string."""
    return (f"Cột '{sc['col']}' có vẻ chưa cập nhật (giống bản {sc['prev']}): "
            f"{sc['same']}/{sc['of']} dòng không đổi dù Actual đã đổi")


def _unsigned(s: str) -> str:
    """Strips a leading '+'/'-' (H3: a word that already carries the direction, e.g. 'hụt', must not also
    be followed by a signed number -- 'hụt plan ngày -33.0%' reads as a double negative)."""
    return s[1:] if s[:1] in "+-" else s


def clause(name: str, e: dict, show_gap: bool = True, f=lambda s: s, cmp_label: str = "MoM") -> str:
    """One channel = one bullet: '**Name**: actual VNĐ · {vượt/hụt} plan ngày Z% · vượt/hụt gap · <growth>'.
    decision 5b/5d (v4.1 charter): the Z bit carries the vượt/hụt word (was a bare '{Z%} vs plan ngày'), and
    base_nho channels use this SAME shape (just a '(base nhỏ)' tag on the Z bit) instead of a separate,
    VND-first early-return shape -- so this clause() text intentionally no longer matches the v3 golden's
    'clause' strings (that divergence is decision 5, not a bug; see REVIEW_v4.md). H3 (v4.2): the Z% next to
    the vượt/hụt word is unsigned -- the word already says the direction."""
    def vnd(s, key):
        return f(marked(e, key, s) + " VNĐ" if key else s + " VNĐ")

    word = "vượt " if e["gap"] >= 0 else "hụt "
    bits = [vnd(e["actual_s"], None)]
    if not e["small"]:
        tag = " (base nhỏ)" if e.get("base_nho") else ""
        bits.append(f"{word}plan ngày {f(_unsigned(marked(e, 'z', e['z_s'])))}{tag}")
    if show_gap:
        bits.append(vnd(e["gap_abs_s"], "gap"))
    if e.get("da_s") is not None:
        bits.append(f"DA {f(marked(e, 'da', e['da_s']))}")
    elif e["mom"] is not None:
        bits.append(f"{f(marked(e, 'mom', e['mom_s']))} {cmp_label}")
    return f"**{name}**: " + " · ".join(bits)


def _pace(e, rest="", on_track=False):
    """'cần chạy 143.1% run-rate kế hoạch' (+ 'khó về target'); already-at-target brands say so. Ported
    verbatim from the retired templates/perf-flash/layout.py::_pace."""
    if e["req_pace"] is None:
        return "đã đạt target" if e["req_rem"] == 0 else ""
    s = (f"Chỉ cần đạt {e['req_pace_s']} nhịp plan phần còn lại để chạm target" if on_track
         else f"cần chạy {e['req_pace_s']} run-rate kế hoạch") + rest
    return s + (" — khó về target" if e["hard"] else "")


def _col(ok, text):
    return f"⟦{'+' if ok else '-'}|{text}⟧"


def _sg(s):
    return f"⟦{'+' if s.startswith('+') else '-'}|{s}⟧" if s[:1] in "+-" else s


def render(facts: dict, notes: dict) -> list:
    """-> blocks: [{"t","l","s"}]. The whole report, deterministic, no LLM (decision 5 + FORBIDDEN).
    Ported from the retired templates/perf-flash/layout.py::render(), with the 5 decision-5 wording changes
    and reading v4 facts' renamed/relocated fields (impact_level, plaus_flags, da_bad/tainted, no cmp_overall/
    cmp_brand/clause/impact on facts -- all built here)."""
    o, B = facts["overall"], facts["brands"]
    tp, E = facts["timepoint"], facts.get("enrich", {})
    is_v3 = bool(facts.get("cmp_label"))
    cmp_short, cmp_overall, cmp_brand = cmp_phrases(facts.get("cmp_label"))
    L = []

    def add(t, s="", l=0):
        L.append({"t": t, "l": l, "s": s})

    def growth_suffix(e):
        if is_v3:
            return f" (DA {marked(e, 'da', e['da_s'])} {cmp_brand})" if e.get("da_s") else ""
        return f" ({marked(e, 'mom', e['mom_s'])} {cmp_brand})" if e["mom"] is not None else ""

    def forecast(e, tail, eoc_s, eoc_gap_abs_s):
        on_track = e["eoc_pct"] is not None and e["eoc_pct"] >= 1
        pace = _pace(e, on_track=on_track) if E.get("required_pace", True) else ""
        return (f"**Forecast:** EOC đạt {eoc_s} VNĐ ({_col(e['eoc_pct'] >= 1, e['eoc_pct_s'])} target{tail})"
                + (f"; {pace}" if pace else "") + ".")

    def channel_bullets(label, e, names, level=1):
        if not names:
            add("li", f"**{label}:** {NONE_MATERIAL}", level)
            return
        add("li", f"**{label}:**", level)
        for c in names:
            add("li", clause(facts["disp"].get(c, c), e["channels"][c], cmp_label=cmp_short), level + 1)

    def fact_bullets(b, level=1, hide_when_empty=False):
        items = notes["brand"].get(b, [])
        if not items:
            if hide_when_empty:  # decision 5a: Highlights omit the line entirely, no placeholder
                return
            add("li", f"**Fact vận hành:** {MISSING}", level)
        elif len(items) == 1:
            add("li", f"**Fact vận hành:** {items[0]}", level)
        else:
            add("li", "**Fact vận hành:**", level)
            for it in items:
                add("li", it, level + 1)

    add("h1", facts["title"])
    if E.get("governing", True):
        bn = facts["bottlenecks"][0] if facts["bottlenecks"] else None
        add("p", (f"Mốc {tp} ({o['run_rate_s']}): đạt {o['progress_s']} target, forecast {_col(o['eoc_pct'] >= 1, o['eoc_pct_s'])} "
                  f"({'hụt' if o['eoc_gap'] < 0 else 'vượt'} {o['eoc_gap_abs_sh']} VNĐ)."
                  + (f" {bn['channel_d']} là điểm nghẽn chính ({bn['share_s']} mức hụt ròng)." if bn else "")))
    add("h2", "📊 OVERALL PERFORMANCE")
    # 5c: Target line keeps full VND digits (plan_s); every other overall VND figure below uses the short form.
    add("li", f"➔ Target & Tiến độ: Target toàn camp: {o['plan_s']} VNĐ | Run-rate mốc {tp} ({o['run_rate_s']}): {o['ptd_sh']} VNĐ.")
    # 5b: "tiến độ X% so với mốc Y% (+Zpp)" replaces the old "đạt X% target camp, chênh lệch Zpp so với run-rate".
    add("li", (f"➔ Actual {tp}: Đạt {o['actual_sh']} VNĐ — tiến độ {o['progress_s']} so với mốc {o['run_rate_s']} "
               f"({_sg(o['y_s'])})."))
    gap_word = "Vượt" if o["gap"] >= 0 else "Hụt"
    add("li", f"{gap_word} plan ngày {_col(o['gap'] >= 0, _unsigned(o['z_s']))} ({o['gap_abs_sh']} VNĐ).", 1)
    if o["mom"] is not None:
        growth = f"{o['mom_s']} (DA {_sg(o['da_s'])})" if o.get("da_s") else _sg(o["mom_s"])
        add("li", f"{cmp_overall[0].upper()}{cmp_overall[1:]}: {growth}.", 1)
    for c in facts.get("cell_bottlenecks", []):
        ratio = f" (gấp {c['ratio_s']} lần gap ròng {c['net_gap_s']})" if c.get("ratio_s") else ""
        add("li", f"⚠️ Điểm nghẽn: {c['brand']} / {c['channel_d']} hụt {c['gap_abs_s']} VNĐ{ratio}.", 1)
    add("li", "➔ Forecast cuối chiến dịch (Forecast EOC = Actual / Tỷ lệ run-rate):")
    add("li", f"Tổng GMV Forecast: {o['eoc_sh']} VNĐ (~{o['eoc_b_s']} VNĐ).", 1)
    add("li", (f"Tỷ lệ hoàn thành dự kiến: {_col(o['eoc_pct'] >= 1, o['eoc_pct_s'])} so với target "
               f"({'thiếu hụt' if o['eoc_gap'] < 0 else 'vượt'} {o['eoc_gap_abs_sh']} VNĐ)."), 1)
    if E.get("required_pace", True) and o["req_pace"] is not None:
        on_track = o["eoc_pct"] is not None and o["eoc_pct"] >= 1
        lead = (f"Chỉ cần đạt {o['req_pace_s']} nhịp plan trong {o['rest_s']} thời gian còn lại để chạm target"
                if on_track else f"Cần chạy {o['req_pace_s']} run-rate kế hoạch trong {o['rest_s']} còn lại")
        add("li", (f"{lead} (còn thiếu {o['req_rem_sh']} VNĐ so với target)" + (" — khó về target." if o["hard"] else ".")), 1)
    d = facts.get("delta")
    if E.get("delta", True) and d:
        add("li", f"➔ So với bản {d['prev_tp']}: Z {d['z_old_s']} → {_sg(d['z_new_s'])}; EOC {d['eoc_old_s']} → {d['eoc_new_s']}.")
        if d["better"]:
            add("li", "Cải thiện (Z): " + "; ".join(f"{x['brand']} {x['pp_s']}" for x in d["better"]) + ".", 1)
        if d["worse"]:
            add("li", "Xấu đi (Z): " + "; ".join(f"{x['brand']} {x['pp_s']}" for x in d["worse"]) + ".", 1)
    for sc in facts.get("stale_cols", []):
        add("li", f"⚠️ {stale_col_message(sc)}.")
    add("hr")

    small = [b for b in facts["brand_order"] if B[b].get("collapsed")]  # 5e: either kind, one shared block

    add("h2", "🟢 HIGHLIGHTS (NHÓM VƯỢT TIẾN ĐỘ)")
    hl = [b for b in facts["highlights"] if not B[b].get("collapsed")]
    if not hl:
        add("li", "Không có brand nào vượt tiến độ.")
    for b in hl:
        e = B[b]
        add("li", f"✅ {b}:")
        add("li", (f"Thực tế {e['actual_s']} VNĐ vs Plan ngày {e['ptd_s']} VNĐ ({_sg(e['z_s'])}, vượt {e['gap_abs_s']} VNĐ) "
                   f"➔ Đạt {e['progress_s']} plan camp{growth_suffix(e)}."), 1)
        channel_bullets("Động lực", e, e["pos"])
        if e["neg"]:
            channel_bullets("Kéo lùi", e, e["neg"])
        fact_bullets(b, hide_when_empty=True)  # 5a
        add("li", forecast(e, "", e["eoc_s"], e["eoc_gap_abs_s"]), 1)
    add("hr")

    add("h2", "🔴 LOWLIGHTS & ĐIỂM NGHẼN")
    ll = [b for b in facts["lowlights"] if not B[b].get("collapsed")]
    if not ll:
        add("li", "Không có brand nào chậm tiến độ.")
    for b in ll:
        e = B[b]
        add("li", f"⚠️ {b} ({impact_label(e['impact_level'])}, {e['contribution_s']} target danh mục):")
        add("li", (f"Thực tế {e['actual_s']} VNĐ vs Plan ngày {e['ptd_s']} VNĐ ({_sg(e['z_s'])}, hụt {e['gap_abs_s']} VNĐ); "
                   f"tiến độ camp đạt {e['progress_s']}{growth_suffix(e)}."), 1)
        channel_bullets("Nguyên nhân", e, e["neg"])
        if e["pos"]:
            channel_bullets("Bù đắp", e, e["pos"])
        fact_bullets(b)
        add("li", forecast(e, f", rủi ro hụt {e['eoc_gap_abs_s']} VNĐ", e["eoc_s"], e["eoc_gap_abs_s"]), 1)
    for bn in facts["bottlenecks"]:
        lst = ", ".join(f"{p['brand']} {p['gap_s']}" for p in bn["per_brand"])
        net_gap_abs_s = bn["net_gap_abs_s"] + WARN if bn.get("net_gap_tainted") else bn["net_gap_abs_s"]
        add("li", (f"⚠️ Điểm nghẽn chung: Kênh {bn['channel_d']} hụt {bn['gap_abs_s']} VNĐ ({bn['share_s']} mức hụt ròng "
                   f"{net_gap_abs_s} VNĐ)" + (f": {lst}." if lst else ".")))

    # H2 (v4.2): "Nhóm brand nhỏ" is its OWN section after Lowlights -- always, one fixed rule, never folded
    # into Highlights even when every collapsed brand happens to be positive this run. One full bullet per
    # brand (actual · {vượt/hụt} plan ngày Z% · gap · Forecast EOC%), same 🟢/🔴 marker as the headlines.
    if small:
        add("hr")
        add("h2", "🟡 NHÓM BRAND NHỎ")
        for b in small:
            e = B[b]
            word = "vượt" if e["gap"] >= 0 else "hụt"
            on_track = e["eoc_pct"] is not None and e["eoc_pct"] >= 1
            add("li", (f"**{b}**: {e['actual_s']} VNĐ · {word} plan ngày {_col(e['gap'] >= 0, _unsigned(marked(e, 'z', e['z_s'])))} · "
                       f"{e['gap_abs_s']} VNĐ · Forecast {_col(on_track, e['eoc_pct_s'])}."))
    return L
