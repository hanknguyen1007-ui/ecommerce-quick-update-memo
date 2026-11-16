"""Facts layer for the "brand-monthly" preset (CHARTER v5): turns the adapter's per-platform raw
series into every number the surface needs, pre-decided (surfaces never compute -- decision 1).
All percentages/shares/"pp" differences are kept as plain fractions (0.05 == 5%/5pp) throughout, so a
"pp" threshold from config.THRESHOLDS compares directly against a fraction difference.
"""
import calendar

from v4.adapters.base import Refuse
from v5 import config as C

T = C.THRESHOLDS
BLOCKS_CHANNEL = ("self_promotion", "affiliate")
BLOCKS_TRAFFIC = ("ads_gmv", "organic")
TOP_BLOCKS = BLOCKS_CHANNEL + BLOCKS_TRAFFIC
DETAILED = ("showcase", "livestream", "video")


def _days_in(ym):
    y, m = ym
    return calendar.monthrange(y, m)[1]


def _prev_month(ym):
    y, m = ym
    return (y - 1, 12) if m == 1 else (y, m - 1)


def _quarter_of(m):
    return (m - 1) // 3 + 1


def _quarter_months(y, q):
    return [(y, 3 * (q - 1) + k) for k in (1, 2, 3)]


def _prev_quarter(y, q):
    return (y - 1, 4) if q == 1 else (y, q - 1)


def _sign(x):
    return 0 if x == 0 else (1 if x > 0 else -1)


class _Period:
    """One platform's time axis: month index lookup + the 4 period definitions (decision 6)."""

    def __init__(self, months, date_update):
        self.idx = {m: i for i, m in enumerate(months)}
        self.cur = (date_update.year, date_update.month)
        if self.cur not in self.idx:
            raise Refuse(f"Date update ({date_update}) không khớp cột tháng nào trong dữ liệu.")
        self.elapsed = date_update.day
        self.prev_month = _prev_month(self.cur)
        q = _quarter_of(self.cur[1])
        cur_q_all = _quarter_months(self.cur[0], q)
        self.cur_q_months = [m for m in cur_q_all if m in self.idx and m <= self.cur]
        py, pq = _prev_quarter(self.cur[0], q)
        prev_q_all = _quarter_months(py, pq)
        self.prev_q_months = prev_q_all if all(m in self.idx for m in prev_q_all) else None
        if self.prev_month not in self.idx:
            raise Refuse(f"Thiếu cột tháng liền trước ({self.prev_month}) để tính MoM.")

    def da(self, series, months, elapsed_last=None):
        total = sum(series[self.idx[m]] for m in months)
        days = sum(_days_in(m) for m in months[:-1])
        days += elapsed_last if elapsed_last is not None else _days_in(months[-1])
        return (total / days if days else 0.0), total, days

    def ratio(self, num_series, den_series, months, elapsed_last=None):
        num = sum(num_series[self.idx[m]] for m in months)
        den = sum(den_series[self.idx[m]] for m in months)
        return (num / den if den else None), num, den

    def assert_runrate(self, time_runrate):
        implied = time_runrate[self.idx[self.cur]] * _days_in(self.cur)
        if abs(implied - self.elapsed) > T["runrate_tol_days"]:
            raise Refuse(f"Time Runrate ({time_runrate[self.idx[self.cur]]:.0%}) không khớp Date update "
                         f"(ngày {self.elapsed}) -- lệch quá {T['runrate_tol_days']} ngày.")


def _mom(per, series):
    da_cur, _, _ = per.da(series, [per.cur], per.elapsed)
    da_prev, _, _ = per.da(series, [per.prev_month])
    delta = da_cur - da_prev
    pct = (delta / da_prev) if da_prev else None
    return {"da_cur": da_cur, "da_prev": da_prev, "delta": delta, "pct": pct,
            "sig": pct is not None and abs(pct) >= T["significance"]}


def _qoq(per, series):
    if per.prev_q_months is None:
        return None
    da_cur, _, _ = per.da(series, per.cur_q_months, per.elapsed)
    da_prev, _, _ = per.da(series, per.prev_q_months)
    delta = da_cur - da_prev
    pct = (delta / da_prev) if da_prev else None
    return {"da_cur": da_cur, "da_prev": da_prev, "delta": delta, "pct": pct,
            "sig": pct is not None and abs(pct) >= T["significance"]}


def _ratio_periods(per, num, den):
    t11, _, _ = per.ratio(num, den, [per.cur], per.elapsed)
    t10, _, _ = per.ratio(num, den, [per.prev_month])
    if per.prev_q_months is not None:
        q4, _, _ = per.ratio(num, den, per.cur_q_months, per.elapsed)
        q3, _, _ = per.ratio(num, den, per.prev_q_months)
    else:
        q4 = q3 = None
    return {"t11": t11, "t10": t10, "q4": q4, "q3": q3}


def _block_facts(per, raw, key, gmv_mom, gmv_qoq, mom_shares_shown, qoq_shares_shown, gmv_da_cur):
    series = raw[key] if key != "organic" else [g - a for g, a in zip(raw["gmv"], raw["ads_gmv"])]
    mom = _mom(per, series)
    qoq = _qoq(per, series)
    share = (mom["da_cur"] / gmv_da_cur) if gmv_da_cur else 0.0
    mom["opposes"] = mom["pct"] is not None and _sign(mom["delta"]) != _sign(gmv_mom["delta"]) and _sign(mom["delta"]) != 0
    mom["share_of_delta"] = (mom["delta"] / gmv_mom["delta"]) if (mom_shares_shown and gmv_mom["delta"]) else None
    if qoq is not None:
        qoq["opposes"] = _sign(qoq["delta"]) != _sign(gmv_qoq["delta"]) and _sign(qoq["delta"]) != 0
        qoq["share_of_delta"] = (qoq["delta"] / gmv_qoq["delta"]) if (qoq_shares_shown and gmv_qoq["delta"]) else None
    return {"key": key, "da": mom["da_cur"], "share": share, "mom": mom, "qoq": qoq}


def _detailed_facts(per, raw, key, gmv_da_cur):
    series = raw[key]
    mom = _mom(per, series)
    qoq = _qoq(per, series)
    small = gmv_da_cur and (mom["da_cur"] / gmv_da_cur) < T["small_base"]
    return {"key": key, "da": mom["da_cur"], "small_base": small, "mom": mom, "qoq": qoq}


def _residual_shift(detailed):
    ls, sc = detailed["livestream"], detailed["showcase"]
    for period in ("mom", "qoq"):
        lp, sp = ls[period], sc[period]
        if lp is None or sp is None or lp["pct"] is None or sp["pct"] is None:
            continue
        if lp["pct"] <= -T["residual_shift"] and sp["pct"] >= T["residual_shift"]:
            return True
    return False


def _lens_signals(blocks, keys, qoq_available):
    items = [(k, blocks[k]) for k in keys]
    largest = max(items, key=lambda kb: kb[1]["share"])[0]
    qoq_anomaly = None
    if qoq_available:
        opposing = [k for k, bl in items if bl["qoq"] is not None and bl["qoq"]["opposes"]]
        if len(opposing) == 1:
            qoq_anomaly = opposing[0]
    pos = [(k, bl) for k, bl in items if bl["mom"]["pct"] is not None and bl["mom"]["pct"] > 0]
    mom_race = None
    if len(pos) == 2:
        (k1, b1), (k2, b2) = pos
        diff = abs(b1["mom"]["pct"] - b2["mom"]["pct"])
        if diff < T["gan_bang_pp"]:
            mom_race = {"type": "gan_bang", "a": k1, "b": k2}
        else:
            fast, other = (k1, k2) if b1["mom"]["pct"] > b2["mom"]["pct"] else (k2, k1)
            if fast != largest:
                mom_race = {"type": "faster", "fast": fast, "other": other}
    falls_both = None
    if qoq_available:
        for k, bl in items:
            if (bl["qoq"]["pct"] is not None and bl["qoq"]["pct"] < 0
                    and bl["mom"]["pct"] is not None and bl["mom"]["pct"] < 0):
                falls_both = k
                break
    return {"largest": largest, "qoq_anomaly": qoq_anomaly, "mom_race": mom_race, "falls_both": falls_both}


def _highlights(blocks, qoq_available):
    if not qoq_available:
        return []
    out = []
    for k in TOP_BLOCKS:
        bl = blocks[k]
        if (bl["qoq"]["pct"] is not None and bl["qoq"]["pct"] > 0
                and bl["mom"]["pct"] is not None and bl["mom"]["pct"] > 0):
            out.append(k)
    return out


def _lowlights(blocks, gmv_mom, gmv_qoq, efficiency, qoq_available):
    """-> list of {"type": "a"|"b"|"c"|"d", ...}, in rule order (decision 12's Lowlight (a)-(d))."""
    out = []
    cost_pairs = (("affiliate_cost", "affiliate"), ("ads_cost", "ads_gmv"))
    for cost_key, gmv_key in cost_pairs:
        cost_mom = efficiency[cost_key]
        block_mom = blocks[gmv_key]["mom"]
        if cost_mom["pct"] is None or block_mom["pct"] is None:
            continue
        if cost_mom["pct"] - block_mom["pct"] >= T["cost_gap_pp"]:
            ratio = efficiency["commission"] if gmv_key == "affiliate" else efficiency["ads_share"]
            ratio_pp = (ratio["t11"] - ratio["t10"]) if (ratio["t11"] is not None and ratio["t10"] is not None) else None
            out.append({"type": "a", "block": gmv_key, "cost_key": cost_key,
                        "cost_mom_pct": cost_mom["pct"], "gmv_mom_pct": block_mom["pct"],
                        "ratio_label": "Commission" if gmv_key == "affiliate" else "Tỷ trọng",
                        "ratio_t11": ratio["t11"], "ratio_pp": ratio_pp})
    for period_name, gmv_period, shares_shown in (
            ("qoq", gmv_qoq, qoq_available and gmv_qoq is not None and gmv_qoq["sig"]),
            ("mom", gmv_mom, gmv_mom["sig"])):
        if gmv_period is None or gmv_period["pct"] is None or gmv_period["pct"] >= 0 or not shares_shown:
            continue
        candidates = [(k, blocks[k][period_name]) for k in TOP_BLOCKS if blocks[k][period_name] is not None]
        k, worst = min(candidates, key=lambda kb: kb[1]["delta"])
        if worst["delta"] < 0:
            out.append({"type": "b", "period": period_name, "block": k, "delta": worst["delta"],
                        "share": worst["share_of_delta"]})
    if qoq_available:
        for k in TOP_BLOCKS:
            bl = blocks[k]
            if (bl["qoq"]["pct"] is not None and bl["qoq"]["pct"] < 0
                    and bl["mom"]["pct"] is not None and bl["mom"]["pct"] < 0):
                out.append({"type": "c", "block": k, "qoq_pct": bl["qoq"]["pct"], "mom_pct": bl["mom"]["pct"]})
    ads_share = efficiency["ads_share"]
    if ads_share["t11"] is not None and ads_share["t10"] is not None:
        diff = ads_share["t11"] - ads_share["t10"]
        if diff >= T["ads_share_up_pp"]:
            out.append({"type": "d", "t11": ads_share["t11"], "t10": ads_share["t10"]})
    return out


def _assert_integrity(raw, n_months):
    """decision 5: SP + Affiliate == GMV; Livestream + Video + Showcase == SP, +-1 VND, on every
    pasted column (not just the current month -- a wrong historical column is still a bad paste)."""
    for i in range(n_months):
        gmv_sum = raw["self_promotion"][i] + raw["affiliate"][i]
        if abs(gmv_sum - raw["gmv"][i]) > 1:
            raise Refuse(f"Self promotion + Affiliate != GMV ở cột tháng {i + 1} "
                         f"({gmv_sum} != {raw['gmv'][i]}) -- dữ liệu nguồn không khớp.")
        sp_sum = raw["livestream"][i] + raw["video"][i] + raw["showcase"][i]
        if abs(sp_sum - raw["self_promotion"][i]) > 1:
            raise Refuse(f"Livestream + Video + Showcase&other != Self promotion ở cột tháng {i + 1} "
                         f"({sp_sum} != {raw['self_promotion'][i]}) -- dữ liệu nguồn không khớp.")


def compute_platform(block):
    raw = block["raw"]
    _assert_integrity(raw, len(block["months"]))
    per = _Period(block["months"], block["date_update"])
    per.assert_runrate(raw["time_runrate"])
    gmv_da_cur, gmv_total_raw, _ = per.da(raw["gmv"], [per.cur], per.elapsed)
    gmv_mom = _mom(per, raw["gmv"])
    gmv_qoq = _qoq(per, raw["gmv"])
    mom_shares_shown = gmv_mom["sig"]
    qoq_shares_shown = gmv_qoq is not None and gmv_qoq["sig"]

    channel = {k: _block_facts(per, raw, k, gmv_mom, gmv_qoq, mom_shares_shown, qoq_shares_shown, gmv_da_cur)
               for k in BLOCKS_CHANNEL}
    traffic = {k: _block_facts(per, raw, k, gmv_mom, gmv_qoq, mom_shares_shown, qoq_shares_shown, gmv_da_cur)
               for k in BLOCKS_TRAFFIC}
    blocks = {**channel, **traffic}
    detailed = {k: _detailed_facts(per, raw, k, gmv_da_cur) for k in DETAILED}

    commission = _ratio_periods(per, raw["affiliate_cost"], raw["affiliate"])
    ads_share = _ratio_periods(per, raw["ads_gmv"], raw["gmv"])
    roi = _ratio_periods(per, raw["gmv"], raw["ads_cost"])
    aff_cost = _mom(per, raw["affiliate_cost"])
    aff_cost["qoq"] = _qoq(per, raw["affiliate_cost"])
    aff_cost["flagged"] = (aff_cost["pct"] is not None and blocks["affiliate"]["mom"]["pct"] is not None
                            and aff_cost["pct"] - blocks["affiliate"]["mom"]["pct"] >= T["cost_gap_pp"])
    ads_cost = _mom(per, raw["ads_cost"])
    ads_cost["qoq"] = _qoq(per, raw["ads_cost"])
    ads_cost["flagged"] = (ads_cost["pct"] is not None and blocks["ads_gmv"]["mom"]["pct"] is not None
                           and ads_cost["pct"] - blocks["ads_gmv"]["mom"]["pct"] >= T["cost_gap_pp"])

    plat_cfg = C.PLATFORMS[block["platform"]]
    qoq_available = gmv_qoq is not None
    efficiency = {"commission": commission, "ads_share": ads_share, "roi": roi,
                  "affiliate_cost": aff_cost, "ads_cost": ads_cost}
    narrative = {
        "channel": _lens_signals(blocks, BLOCKS_CHANNEL, qoq_available),
        "traffic": _lens_signals(blocks, BLOCKS_TRAFFIC, qoq_available),
        "highlights": _highlights(blocks, qoq_available),
        "lowlights": _lowlights(blocks, gmv_mom, gmv_qoq, efficiency, qoq_available),
    }
    return {
        "key": block["platform"], "name": plat_cfg["display"], "heading": plat_cfg["heading"],
        "icon": plat_cfg["icon"],
        "brand": block["brand"], "cutoff": f"{block['date_update'].day}/{block['date_update'].month}",
        "month_no": per.cur[1], "year": per.cur[0], "prev_month_no": per.prev_month[1],
        "q_cur": _quarter_of(per.cur[1]), "q_prev": _quarter_of(per.prev_q_months[0][1]) if per.prev_q_months else None,
        "elapsed_days": per.elapsed, "gmv_total_raw": gmv_total_raw,
        "qoq_available": qoq_available,
        "gmv": {"da": gmv_da_cur, "mom": gmv_mom, "qoq": gmv_qoq,
                "mom_shares_shown": mom_shares_shown, "qoq_shares_shown": qoq_shares_shown},
        "blocks": blocks, "detailed": detailed,
        "efficiency": efficiency,
        "flags": {"residual_shift": _residual_shift(detailed)},
        "narrative": narrative,
    }


def compute(parsed_blocks):
    """parsed_blocks: the adapter's output (already brand/platform-validated, Shopee-then-TikTok order).
    -> {"brand": str, "platforms": [platform_facts, ...]}."""
    platforms = [compute_platform(b) for b in parsed_blocks]
    return {"brand": parsed_blocks[0]["brand"], "platforms": platforms}
