"""Deterministic text surface for the "brand-monthly" preset (CHARTER v5, decisions 12-14). Pure
formatting: every number, boolean and block selection already lives in the facts dict (v5/facts.py).
No sentence here exists outside decision 12's fixed templates.
"""
from v5 import numfmt as M
from v5 import config as C

T = C.THRESHOLDS

BLOCK_HEAD = {"self_promotion": "Self promotion", "affiliate": "Affiliate",
              "ads_gmv": "Ads GMV", "organic": "Organic GMV"}
BLOCK_SHORT = {"self_promotion": "Self promotion", "affiliate": "Affiliate",
               "ads_gmv": "Ads", "organic": "Organic"}
DETAIL_LABEL = {"livestream": "Livestream", "video": "Video", "showcase": "Showcase&other"}
CHANNEL_HEADING = "1. KÊNH BÁN (Self promotion + Affiliate = 100%)"
TRAFFIC_HEADING = "2. NGUỒN TRAFFIC (Ads + Organic = 100%)"


def _e(x):
    return "🟢" if x >= 0 else "🔴"


def _li(text, lvl=0, brk=False):
    return {"type": "li" if lvl == 0 else "li2", "text": text, "break": brk}


def _p(text, merge_up=False):
    return {"type": "p", "text": text, "merge_up": merge_up}


# ---------- shared value formatting ----------

def _sig_pct(period, nd=1):
    s = M.pct(period["pct"], nd, signed=True)
    return _e(period["pct"]), (f"**{s}**" if period["sig"] else s)


def _recap_metric(period):
    e, s = _sig_pct(period)
    tag = "" if period["sig"] else " (đi ngang)"
    return f"{e} {s}{tag}"


def _gmv_body_line(label, period, base_label, base_value):
    e, s = _sig_pct(period)
    tag = " · đi ngang" if not period["sig"] else ""
    return (f"{label}: {e} {s} · {M.money_m(period['delta'], signed=True)} "
            f"({base_label}: {M.money_m(period['da_prev'])}){tag}")


def _block_metric_line(label, period, gmv_sig):
    """gmv_sig: whether the overall GMV's own change in this SAME period is significant -- gates the
    bold on sub-block %Δ lines (decision 12/13: body bolding flags a period the headline already
    flagged as notable)."""
    e = _e(period["pct"])
    s = f"**{M.pct(period['pct'], 1, signed=True)}**" if gmv_sig else M.pct(period["pct"], 1, signed=True)
    share = ""
    if period.get("share_of_delta") is not None:
        if period["opposes"]:
            share = " · ngược chiều"
        else:
            word = "mức tăng" if period["delta"] >= 0 else "mức giảm"
            share = f" · {M.pct(period['share_of_delta'], 0)} {word}"
    return f"{label}: {e} {s} · {M.money_m(period['delta'], signed=True)}{share}"


def _detail_line(key, d):
    name = DETAIL_LABEL[key]
    if d["small_base"]:
        return f"**{name}**: {M.money_m(d['da'])} · base nhỏ"
    qoq = f"QoQ {_e(d['qoq']['pct'])} {M.pct(d['qoq']['pct'], 1, signed=True)}" if d["qoq"] else None
    mom = f"MoM {_e(d['mom']['pct'])} {M.pct(d['mom']['pct'], 1, signed=True)}"
    parts = " · ".join(x for x in (qoq, mom) if x)
    warn = " ⚠️" if d.get("flagged") else ""
    return f"**{name}**: {M.money_m(d['da'])} · {parts}{warn}"


def _ratio_line(label, r, nd=1, unit="%"):
    bold_t11 = (r["t11"] is not None and r["t10"] is not None
                and abs(r["t11"] - r["t10"]) >= T["giu_pp"])
    t11 = f"**{M.pct(r['t11'], nd, unit=unit)}**" if bold_t11 else M.pct(r["t11"], nd, unit=unit)
    parts = []
    if r["q4"] is not None and r["q3"] is not None:
        parts.append(f"Q{{q_cur}} {M.pct(r['q4'], nd, unit=unit)} (Q{{q_prev}}: {M.pct(r['q3'], nd, unit=unit)})")
    parts.append(f"T{{m_cur}} {t11} (T{{m_prev}}: {M.pct(r['t10'], nd, unit=unit)})")
    return f"**{label}**: " + " · ".join(parts)


def _ratio_line_ratio(label, r, nd=2):
    """Same as _ratio_line but for a plain ratio (ROI): no %, bold T11 on relative-change >= giu_pp."""
    bold_t11 = (r["t11"] is not None and r["t10"] not in (None, 0)
                and abs((r["t11"] - r["t10"]) / r["t10"]) >= T["giu_pp"])
    t11 = f"**{M.ratio(r['t11'], nd)}**" if bold_t11 else M.ratio(r["t11"], nd)
    parts = []
    if r["q4"] is not None and r["q3"] is not None:
        parts.append(f"Q{{q_cur}} {M.ratio(r['q4'], nd)} (Q{{q_prev}}: {M.ratio(r['q3'], nd)})")
    parts.append(f"T{{m_cur}} {t11} (T{{m_prev}}: {M.ratio(r['t10'], nd)})")
    return f"**{label}**: " + " · ".join(parts)


def _cost_line(label, cost):
    """decision 12's Lowlight (a) condition also drives this one line's own MoM bold (ported 1:1 from
    the same cost-vs-GMV-growth gap): no 🟢/🔴 ever (rule 8), bold only when that gap fired."""
    qoq = f"QoQ {M.pct(cost['qoq']['pct'], 1, signed=True)}" if cost["qoq"] else None
    mom_s = M.pct(cost["pct"], 1, signed=True)
    mom = f"MoM {'**' + mom_s + '**' if cost.get('flagged') else mom_s}"
    parts = " · ".join(x for x in (qoq, mom) if x)
    return f"**{label}**: {M.money_m(cost['da_cur'])}/ngày · {parts}"


def _fill(tmpl, pf):
    return tmpl.format(q_cur=pf["q_cur"], q_prev=pf["q_prev"], m_cur=pf["month_no"], m_prev=pf["prev_month_no"])


# ---------- takeaways (decision 12) ----------

def _channel_takeaway(pf):
    sig = pf["narrative"]["channel"]
    blocks = pf["blocks"]
    parts = [f"{BLOCK_SHORT[sig['largest']]} chiếm **{M.pct(blocks[sig['largest']]['share'], 0)}** GMV"]
    if sig["qoq_anomaly"]:
        k = sig["qoq_anomaly"]
        word = "tăng" if blocks[k]["qoq"]["pct"] >= 0 else "giảm"
        parts.append(f"{BLOCK_SHORT[k]} là block duy nhất {word} QoQ "
                      f"(**{M.pct(blocks[k]['qoq']['pct'], 1, signed=True)}**)")
    race = sig["mom_race"]
    if race and race["type"] == "faster":
        f_, o_ = race["fast"], race["other"]
        parts.append(f"{BLOCK_SHORT[f_]} tăng MoM nhanh hơn (**{M.pct(blocks[f_]['mom']['pct'], 1, signed=True)}** "
                      f"so với {M.pct(blocks[o_]['mom']['pct'], 1, signed=True)})")
    elif race and race["type"] == "gan_bang":
        a, b = race["a"], race["b"]
        parts.append(f"{BLOCK_SHORT[a]} và {BLOCK_SHORT[b]} tăng MoM gần bằng nhau "
                      f"({M.pct(blocks[a]['mom']['pct'], 1, signed=True)} và "
                      f"{M.pct(blocks[b]['mom']['pct'], 1, signed=True)})")
    if sig["falls_both"]:
        k = sig["falls_both"]
        parts.append(f"{BLOCK_SHORT[k]} giảm cả QoQ lẫn MoM")
    return "*" + "; ".join(parts) + ".*"


def _traffic_takeaway(pf):
    sig = pf["narrative"]["traffic"]
    blocks = pf["blocks"]
    eff = pf["efficiency"]["ads_share"]
    diff = eff["t11"] - eff["t10"]
    if abs(diff) < T["giu_pp"]:
        parts = [f"Tỷ trọng Ads giữ **{M.pct(eff['t11'], 0)}**"]
    else:
        parts = [f"Tỷ trọng Ads **{M.pct(eff['t11'], 0)}** (T10: {M.pct(eff['t10'], 0)})"]
    if sig["qoq_anomaly"]:
        k = sig["qoq_anomaly"]
        word = "tăng" if blocks[k]["qoq"]["pct"] >= 0 else "giảm"
        parts.append(f"{BLOCK_SHORT[k]} là block duy nhất {word} QoQ "
                      f"(**{M.pct(blocks[k]['qoq']['pct'], 1, signed=True)}**)")
    race = sig["mom_race"]
    if race and race["type"] == "faster":
        f_, o_ = race["fast"], race["other"]
        parts.append(f"{BLOCK_SHORT[f_]} tăng MoM nhanh hơn (**{M.pct(blocks[f_]['mom']['pct'], 1, signed=True)}** "
                      f"so với {M.pct(blocks[o_]['mom']['pct'], 1, signed=True)})")
    elif race and race["type"] == "gan_bang":
        a, b = race["a"], race["b"]
        parts.append(f"{BLOCK_SHORT[a]} và {BLOCK_SHORT[b]} tăng MoM gần bằng nhau "
                      f"({M.pct(blocks[a]['mom']['pct'], 1, signed=True)} và "
                      f"{M.pct(blocks[b]['mom']['pct'], 1, signed=True)})")
    if sig["falls_both"]:
        k = sig["falls_both"]
        parts.append(f"{BLOCK_SHORT[k]} giảm cả QoQ lẫn MoM")
    return "*" + "; ".join(parts) + ".*"


# ---------- quick recap ----------

def _overall_recap_line(pf):
    gmv = pf["gmv"]
    line = f"{pf['icon']} **{pf['name']}** ({pf['cutoff']}): DA **{M.money_m(gmv['da'])}**"
    if pf["qoq_available"]:
        line += f" · QoQ {_recap_metric(gmv['qoq'])}"
    line += f" · MoM {_recap_metric(gmv['mom'])}"
    return line


def _highlight_line(pf, key):
    bl = pf["blocks"][key]
    return (f"**{pf['name']}**: {BLOCK_SHORT[key]} tăng cả QoQ (**{M.pct(bl['qoq']['pct'], 1, signed=True)}**) "
            f"lẫn MoM (**{M.pct(bl['mom']['pct'], 1, signed=True)}**)")


def _lowlight_lines(pf, low):
    name = pf["name"]
    if low["type"] == "a":
        pp = M.pct(low["ratio_pp"], 1, signed=True, unit="pp") if low["ratio_pp"] is not None else ""
        return (f"**{name}**: Cost {BLOCK_SHORT[low['block']]}/ngày "
                f"**{M.pct(low['cost_mom_pct'], 1, signed=True)}** trong khi GMV {BLOCK_SHORT[low['block']]} "
                f"{M.pct(low['gmv_mom_pct'], 1, signed=True)} · {low['ratio_label']} "
                f"**{M.pct(low['ratio_t11'], 1)}** ({pp})")
    if low["type"] == "b":
        label = "QoQ" if low["period"] == "qoq" else "MoM"
        return (f"**{name}** {label}: {BLOCK_SHORT[low['block']]} **{M.money_m(low['delta'], signed=True)}** "
                f"({M.pct(low['share'], 0)} mức giảm)")
    if low["type"] == "c":
        return (f"**{name}**: {BLOCK_SHORT[low['block']]} giảm cả QoQ (**{M.pct(low['qoq_pct'], 1, signed=True)}**) "
                f"lẫn MoM (**{M.pct(low['mom_pct'], 1, signed=True)}**)")
    return f"**{name}**: tỷ trọng Ads **{M.pct(low['t11'], 0)}** (T10: {M.pct(low['t10'], 0)})"


# ---------- platform body ----------

def _platform_body(pf):
    out = []
    out.append({"type": "h2", "text": f"{pf['icon']} {pf['heading'].upper()} · Cutoff {pf['cutoff']} · "
                                       f"GMV {M.money_b(pf['gmv_total_raw'])} VNĐ ({pf['elapsed_days']} ngày)"})
    out.append(_li(f"➔ **GMV: {M.money_m(pf['gmv']['da'])}/ngày**"))
    if pf["qoq_available"]:
        out.append(_li(_gmv_body_line("QoQ", pf["gmv"]["qoq"], f"Q{pf['q_prev']}", pf["gmv"]["qoq"]["da_prev"])))
    out.append(_li(_gmv_body_line("MoM", pf["gmv"]["mom"], f"T{pf['prev_month_no']}", pf["gmv"]["mom"]["da_prev"])))

    for heading, keys, takeaway_fn in ((CHANNEL_HEADING, ("self_promotion", "affiliate"), _channel_takeaway),
                                        (TRAFFIC_HEADING, ("ads_gmv", "organic"), _traffic_takeaway)):
        out.append({"type": "h3", "text": heading})
        out.append(_p(takeaway_fn(pf), merge_up=True))
        for key in keys:
            bl = pf["blocks"][key]
            out.append(_li(f"➔ **{BLOCK_HEAD[key]}: {M.money_m(bl['da'])}/ngày · {M.pct(bl['share'], 0)} GMV**"))
            gmv_sig_qoq = pf["gmv"]["qoq_shares_shown"] if pf["qoq_available"] else False
            if bl["qoq"] is not None:
                out.append(_li(_block_metric_line("QoQ", bl["qoq"], gmv_sig_qoq)))
            out.append(_li(_block_metric_line("MoM", bl["mom"], pf["gmv"]["mom_shares_shown"])))
            if key == "self_promotion":
                out.append(_li("**Detailed:**"))
                for dk in ("showcase", "livestream", "video"):
                    out.append(_li(_detail_line(dk, pf["detailed"][dk]), lvl=1))
            elif key == "affiliate":
                out.append(_li(_fill(_ratio_line("Commission", pf["efficiency"]["commission"]), pf)))
                out.append(_li(_cost_line("Cost", pf["efficiency"]["affiliate_cost"])))
            elif key == "ads_gmv":
                out.append(_li(_fill(_ratio_line("Tỷ trọng", pf["efficiency"]["ads_share"], nd=0), pf)))
                out.append(_li(_cost_line("Cost", pf["efficiency"]["ads_cost"])))
                out.append(_li(_fill(_ratio_line_ratio("ROI", pf["efficiency"]["roi"]), pf)))
    return out


def render(facts):
    """facts: v5.facts.compute()'s output. -> (recap_blocks, full_blocks) -- recap_blocks is the
    Messenger cut (decision 14: title through Lowlights); full_blocks is the whole Docs/md report."""
    for pf in facts["platforms"]:
        pf["detailed"]["livestream"]["flagged"] = pf["flags"]["residual_shift"]
        pf["detailed"]["showcase"]["flagged"] = pf["flags"]["residual_shift"]

    blocks = [_p(f"**{facts['brand'].upper()} — BRAND PERFORMANCE UPDATE "
                 f"(T{facts['platforms'][0]['month_no']}/{facts['platforms'][0]['year']})**"),
              _li("**⚡ QUICK RECAP**", brk=True)]
    for pf in facts["platforms"]:
        blocks.append(_li(_overall_recap_line(pf)))

    highlight_lines = [_highlight_line(pf, k) for pf in facts["platforms"] for k in pf["narrative"]["highlights"]]
    lowlight_lines = [_lowlight_lines(pf, low) for pf in facts["platforms"] for low in pf["narrative"]["lowlights"]]
    if len(highlight_lines) + len(lowlight_lines) > 10:
        highlight_lines = highlight_lines[:max(0, 10 - len(lowlight_lines))]

    if highlight_lines:
        blocks.append(_li("🟢 **Highlights**", brk=True))
        blocks += [_li(t) for t in highlight_lines]
    if lowlight_lines:
        blocks.append(_li("🔴 **Lowlights**", brk=True))
        blocks += [_li(t) for t in lowlight_lines]

    recap_blocks = list(blocks)

    for i, pf in enumerate(facts["platforms"]):
        blocks.append({"type": "hr", "text": ""})
        blocks += _platform_body(pf)

    return recap_blocks, blocks
