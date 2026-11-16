"""v3 adapter: the perf-flash v3 ("Plan Up to Date") export layout (Plan Up to Date / Total Actual /
% Required / <cmp> Actual). NOTE: this is NOT the "Platform Drill Down" project/export -- that is a
different, unrelated data source; the name collision in an earlier draft of this file was wrong (S5).
Ported from templates/perf-flash/compute.py::_parse_v3 (same parsing rules), rewired onto the generic
synonym/ambiguity-refusal column resolver in base.py (decision 2) and the shared facts.py row contract
(decision 1). Comparison columns (growth/DA) are OPTIONAL: when absent, has_comparison/has_da are False and
the facts/surfaces layer hides DA lines instead of failing (G3)."""
import re

from core import tsv as T
from v4.adapters.base import Refuse, resolve_columns

NAME = "v3"

SYNONYMS = {
    "ptd": [r"^plan up to date$"],
    "actual": [r"^total actual$"],
    "gap": [r"^gap am+ount$"],
    "zpct": [r"^%\s*gap vs plan$"],
    "progresspct": [r"^%\s*total actual$"],
    "runrate": [r"^%\s*required$"],
    "growthpct": [r"^gmv vs\s"],
    "dapct": [r"^da gmv vs\s"],
}
REQUIRED = {"ptd", "actual", "gap", "zpct", "progresspct", "runrate"}
OPTIONAL_COMPARISON = {"growthpct", "dapct"}


def sniff(lines):
    return any(any(T.fold(c) == "plan up to date" for c in cells) for cells in lines[:12])


def _v3_channel(label, ch):
    label = re.sub(r"^↳\s*", "", label.strip())
    f = T.fold(label)
    table = {T.fold(ch["affiliate"]): ch["affiliate"], T.fold(ch["self_sell"]): ch["self_sell"],
             "live": ch["self_children"][0], "video": ch["self_children"][1],
             "showcase & other": ch["self_children"][2], "showcase": ch["self_children"][2]}
    return table.get(f)


def _display(brand, schema):
    """C2 (CHARTER v4.3): no brand registry/alias lookup -- brand identity is the label exactly as pasted
    (trimmed/NFC-normalized via T.norm; `schema` param kept only so call sites don't need to change)."""
    return T.norm(brand or "")


def _month_num(s):
    m = re.search(r"(\d{1,2})", s or "")
    return m.group(1) if m else None


def _parse_ngay_chot(s):
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", (s or "").strip())
    if not m:
        return None
    mm, dd, yyyy = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if not 1 <= mm <= 12:
        return None
    return {"mm": mm, "dd": dd, "yyyy": yyyy, "dm": f"{dd:02d}.{mm:02d}", "ambiguous": dd <= 12}


def _header_fields(lines):
    """R3 (CHARTER v4.4): no longer depends on a separate '02 Current'/'03 Comparision' marker row (the
    '01 PHẠM VI PHÂN TÍCH' line) to tell which Month/Year pair is current vs comparison -- a real paste may
    start right at the 'Platform' row, dropping that marker line entirely, which used to leave cur_col/
    cmp_col both None and silently route EVERYTHING (including the comparison Month/Year) into `flat`,
    where the second "month"/"year" write clobbered the first and the title lost the current month/year.
    Positional rule instead: for a label repeated in this header block (Month, Year), the FIRST occurrence
    is the current period's value, the SECOND is the comparison period's -- true whether or not the marker
    row is present, since it always lists current-period fields before comparison-period fields."""
    flat, cur, cmp_, seen = {}, {}, {}, set()
    for cells in lines:
        for i in range(0, len(cells) - 1, 2):
            label, value = cells[i].strip(), cells[i + 1].strip()
            if not label or not value:
                continue
            fl = T.fold(label)
            if fl not in seen:
                seen.add(fl)
                flat[fl] = value
                cur[fl] = value
            else:
                cmp_[fl] = value
    return flat, cur, cmp_


def mapping_preview(text):
    """Column-mapping preview for the user to confirm before parsing (decision 2). Refuses on ambiguity,
    same as parse() -- this lets the UI show the preview and the refusal reason together."""
    lines = T.split_text(text)
    hdr_i = next((i for i, cells in enumerate(lines[:12]) if any(T.fold(c) == "plan up to date" for c in cells)), None)
    if hdr_i is None:
        raise Refuse("Không tìm thấy dòng header v3 ('Plan Up to Date')")
    _, preview = resolve_columns(lines[hdr_i], SYNONYMS, REQUIRED)
    return preview


def _dup_cmp_anomaly(order, data, schema, add):
    """Same non-zero <cmp> Actual repeated across sibling channels of one brand: usually a paste/mapping
    error. Taints those rows' DA display in place (x["da_bad"]=True -> facts.compute()'s da_of() appends
    WARN). Ported from the pinned templates/perf-flash/compute.py::_dup_cmp_anomaly."""
    ch = schema["channels"]
    leaves = [ch["affiliate"], ch["self_sell"], *ch["self_children"]]
    for b in order:
        seen = {}
        for c in leaves:
            v = data[b].get(c, {}).get("last")
            if v:
                seen.setdefault(v, []).append(c)
        for v, cs in seen.items():
            if len(cs) > 1:
                add("Trùng Actual kỳ so sánh (v3)", "warn",
                    f"{b}: {', '.join(_dn(schema, c) for c in cs)} cùng giá trị {v:,} ở cột actual kỳ so sánh "
                    "— nghi trùng/lỗi nhập")
                for c in cs:
                    data[b][c]["x"]["da_bad"] = True


def _dn(schema, c):
    return schema.get("channel_display", {}).get(c, c)


def _v3_extra_checks(order, data, schema, add, grand_total, k_values):
    """v3-only integrity, adapter-local (needs the raw row x-dicts, not just facts): run-rate ("% Required")
    must be identical across every row; Σ brand must equal the Total EC2 row; the DA growth constant k must
    hold within tolerance."""
    rrs = [d["x"]["runrate_col"] for b in order for d in data[b].values() if d["x"].get("runrate_col") is not None]
    tol = schema["checks"]["v3_runrate_tol_pp"]
    if rrs and max(rrs) - min(rrs) > tol:
        add("Run-rate đồng nhất (% Required)", "fail", f"dao động {min(rrs):.2f}%–{max(rrs):.2f}%, vượt ±{tol}pp")
    elif rrs:
        add("Run-rate đồng nhất (% Required)", "ok", f"mọi dòng = {rrs[0]:.2f}%")
    if grand_total:
        # R2 (CHARTER v4.4): check every PASTED column the grand-total row actually carries --
        # plan to date, actual, AND the comparison-period actual ("last") when present. Never "plan"
        # (always derived here, no Plan column in this layout).
        tol_vnd = schema["checks"]["tolerance_vnd"]
        measures = [m for m in ("ptd", "actual", "last") if grand_total.get(m) is not None]
        msgs = []
        for m in measures:
            s = sum(data[b][schema["channels"]["total"]][m] for b in order)
            if abs(s - grand_total[m]) > tol_vnd:
                msgs.append(f"{m}: tổng brand {s:,} ≠ Total EC2 {grand_total[m]:,} (lệch {s - grand_total[m]:,})")
        add("Σ brand = Total EC2", "fail" if msgs else "ok",
            "; ".join(msgs) if msgs else f"{len(order)} brand, {', '.join(measures)} khớp Total EC2")
    if k_values:
        kmin, kmax, kmean = min(k_values), max(k_values), sum(k_values) / len(k_values)
        ktol = schema["checks"]["k_tolerance"]
        if kmax - kmin > ktol:
            add("Hệ số k (DA growth)", "warn", f"k dao động {kmin:.4f}–{kmax:.4f} (>±{ktol}), DA GMV có thể tính sai")
        else:
            add("Hệ số k (DA growth)", "ok", f"k = {kmean:.4f} (n={len(k_values)})")
        for b in order:
            for d in data[b].values():
                if d["x"].get("k") is not None and abs(d["x"]["k"] - kmean) > ktol:
                    d["x"]["da_bad"] = True


def parse(lines, add):
    hdr_i = next((i for i, cells in enumerate(lines[:12]) if any(T.fold(c) == "plan up to date" for c in cells)), None)
    if hdr_i is None:
        raise Refuse("Không tìm thấy dòng header v3 ('Plan Up to Date')")
    header = lines[hdr_i]
    idx_m, preview = resolve_columns(header, SYNONYMS, REQUIRED)
    idx = {k: v.index for k, v in idx_m.items()}
    has_comparison = all(idx[k] is not None for k in OPTIONAL_COMPARISON)
    cands = [i for i, c in enumerate(header) if T.fold(c).endswith("actual") and i != idx.get("actual")]
    idx["cmp_actual"] = cands[-1] if (cands and has_comparison) else None
    add("Cột bắt buộc (v3)", "ok", f"Đủ {len(REQUIRED)} cột bắt buộc" + ("; có cột so sánh (DA/growth)" if has_comparison
        else "; KHÔNG có cột so sánh -- bỏ qua DA/growth (chỉ hiện khi có)"))

    cmp_label = (re.sub(r"(?i)^gmv vs\s*", "", header[idx["growthpct"]]).strip() or "kỳ trước") if has_comparison else None
    flat, cur, _ = _header_fields(lines[:hdr_i])
    platform, campaign = flat.get("platform", "").strip(), flat.get("campaign", "").strip()
    period, hour = flat.get("period", "").strip(), flat.get("hour", "").strip()
    cur_mn, cur_yr = _month_num(cur.get("month", "")), cur.get("year", "").strip()
    nc_raw = flat.get("ngày chốt", "")
    nc = _parse_ngay_chot(nc_raw)
    missing = [lbl for lbl, v in (("Platform", platform), ("Campaign", campaign), ("Period", period),
                                   ("Hour", hour), ("02 Current Year/Month", cur_mn and cur_yr),
                                   ("Ngày chốt", nc)) if not v]
    if missing:
        add("Tiêu đề/Mốc gợi ý (v3)", "warn", "Thiếu trường header: " + ", ".join(missing)
            + " -- phần gợi ý tương ứng để trống, cần tự điền (ghi đè tay vẫn được giữ)")
    if nc and nc["ambiguous"]:
        add("Ngày chốt (v3)", "warn", f"'{nc_raw}' mơ hồ (ngày {nc['dd']} ≤ 12, có thể đọc cả hai chiều) -- đã hiểu "
            f"là tháng {nc['mm']}/ngày {nc['dd']}/{nc['yyyy']} (Excel M/D/Y); xác nhận lại nếu khác")
    head = " — ".join(x for x in (platform.upper(), campaign.upper()) if x)
    title_guess = " ".join(x for x in (head, f"{cur_mn}/{cur_yr}" if cur_mn and cur_yr else "") if x)
    if period:
        title_guess = f"{title_guess} ({period})" if title_guess else f"({period})"
    tp_guess = " ".join(x for x in (hour, nc["dm"] if nc else "") if x)
    suggest = {"title": title_guess, "timepoint": tp_guess, "cmp_label": cmp_label}

    from v4.facts import SCHEMA  # default channel/threshold config shared with facts.py
    ch, thresholds = SCHEMA["channels"], SCHEMA["thresholds"]
    data, order, grand_total, k_values = {}, [], None, []
    cur_brand, cur_brand_ptd, bad, noname = None, 0, 0, 0
    for off, row in enumerate(lines[hdr_i + 1:]):
        ln = hdr_i + 2 + off
        if not any(c.strip() for c in row):
            continue
        row = row + [""] * max(0, len(header) - len(row))
        label = row[0].strip()
        try:
            ptd, actual, gap = (T.to_int(row[idx[k]]) for k in ("ptd", "actual", "gap"))
            zpct, progpct, rrpct = (T.to_pct(row[idx[k]]) for k in ("zpct", "progresspct", "runrate"))
            growthpct = T.to_pct(row[idx["growthpct"]]) if has_comparison else None
            dapct = T.to_pct(row[idx["dapct"]]) if has_comparison else None
            cmp_actual = T.to_int(row[idx["cmp_actual"]]) if idx.get("cmp_actual") is not None else None
        except ValueError as e:
            add("Số liệu (v3)", "fail", f"dòng {ln}: {e}", row=ln)
            bad += 1
            continue
        if ptd is None or actual is None or not rrpct:
            add("Số liệu (v3)", "fail", f"dòng {ln}: thiếu Plan Up to Date / Total Actual / % Required", row=ln)
            bad += 1
            continue
        x = {"gap": gap, "progress": progpct, "z_col": zpct, "mom": growthpct, "da": dapct, "runrate_col": rrpct}
        if not label:
            if grand_total is None:
                grand_total = {"ptd": ptd, "actual": actual, "last": cmp_actual, "x": x}
            else:
                noname += 1
            continue
        plan_full = round(ptd / (rrpct / 100))
        # R1 (CHARTER v4.4): channel rows are recognised by the CHANNEL VOCABULARY (existing channel
        # aliases, trimmed, case-insensitive), with or without "↳" and leading spaces -- not by requiring
        # the "↳" prefix to be present at all (real pastes sometimes drop it, which used to make every
        # channel row read as a brand: "Live / TOTAL bị lặp" x30). An arrow that IS present but doesn't
        # match any known channel name is still flagged (a likely typo), not silently turned into a brand.
        chan = _v3_channel(label, ch)
        has_arrow = bool(re.match(r"^\s*↳", label))
        if chan is None and has_arrow:
            add("Kênh lạ (v3)", "warn", f"dòng {ln}: không nhận diện kênh '{label}'")
            continue
        is_child = chan is not None
        if is_child:
            if cur_brand is None:
                add("Dữ liệu (v3)", "fail", f"dòng {ln}: kênh con '{label}' không có brand phía trên", row=ln)
                bad += 1
                continue
            brand = cur_brand
            if ptd and cur_brand_ptd and ptd < thresholds["base_nho_share"] * cur_brand_ptd \
                    and abs(actual / ptd - 1) > thresholds["base_nho_z"]:
                x["base_nho"] = True
        else:
            brand = _display(label, SCHEMA)
            chan = ch["total"]
            if brand not in data:
                data[brand] = {}
                order.append(brand)
            cur_brand, cur_brand_ptd = brand, ptd
        if chan in data.setdefault(brand, {}):
            add("Trùng dòng (v3)", "fail", f"dòng {ln}: {brand} / {chan} bị lặp", row=ln)
            bad += 1
            continue
        data[brand][chan] = {"plan": plan_full, "ptd": ptd, "actual": actual, "last": cmp_actual or 0,
                             "line": ln, "x": x}
        if growthpct is not None and dapct is not None and abs(dapct + 100) > 1e-9:
            k = (1 + growthpct / 100) / (1 + dapct / 100)
            x["k"] = k
            k_values.append(k)
    if noname:
        add("Dòng thiếu Brand (v3)", "warn", f"{noname} dòng trống Brand bị bỏ qua (ngoài dòng grand total)")
    if bad:
        raise Refuse(f"{bad} dòng lỗi số liệu (v3) -- xem checks để biết dòng nào")
    if not data:
        raise Refuse("Không đọc được brand nào (v3)")
    need = [ch["total"], ch["affiliate"], ch["self_sell"], *ch["self_children"]]
    for b in order:
        lack = [c for c in need if c not in data[b]]
        if lack:
            raise Refuse(f"{b}: thiếu kênh {', '.join(lack)} (v3)")
    add("Đủ kênh (v3)", "ok", f"{len(order)} brand × {len(need)} kênh")
    _v3_extra_checks(order, data, SCHEMA, add, grand_total, k_values)
    if has_comparison:
        _dup_cmp_anomaly(order, data, SCHEMA, add)
    caps = {"has_comparison": has_comparison, "has_da": has_comparison, "has_channels": True,
            "has_platforms": bool(platform)}
    extra = {"cmp_label": cmp_label, "suggest": suggest, "grand_total": grand_total, "k_values": k_values,
             "platform": platform or None, "runrate_col": header[idx["runrate"]] if idx.get("runrate") is not None else None,
             "caps": caps, "mapping_preview": preview,
             # R2 (CHARTER v4.4): this layout has no pasted Plan column -- "plan" is always derived
             # (ptd / % Required) and must never be re-asserted by facts._integrity().
             "integrity_measures": ("ptd", "actual", "last")}
    return order, data, extra
