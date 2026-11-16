"""v2 adapter: the original Brand/Kênh/Plan/GMV plan up to date/Actual/Actual tháng trước layout, one row
per brand x channel. Ported from the retired templates/perf-flash/compute.py::_parse_v2, rewired onto the
generic synonym/ambiguity-refusal column resolver (decision 2) and the shared facts.py row contract
(decision 1). This layout has no comparison/DA columns -- has_comparison/has_da are always False, and
facts/surfaces hide the DA line automatically (caps, G3 extensibility)."""
import re

from core import tsv as T
from v4.adapters.base import Refuse, resolve_columns

NAME = "v2"

SYNONYMS = {
    "brand": [r"^brand$"],
    "channel": [r"^kênh$"],
    "plan": [r"^plan$"],
    "ptd": [r"^gmv plan up to date$"],
    "actual": [r"^actual(?! tháng)(?! vs)"],
    "last": [r"^actual tháng trước$"],
    # optional precomputed columns: only cross-checked by facts._crosscheck, never used for the numbers themselves
    "progress": [r"^tiến độ thực tế$"],
    "gap": [r"^vượt / thiếu$"],
    "z_col": [r"^actual vs plan ngày$"],
    "mom": [r"^so với tháng trước$"],
}
REQUIRED = {"brand", "channel", "plan", "ptd", "actual"}


def sniff(lines):
    hdr = next((cells for cells in lines[:5] if any(T.fold(c) == "brand" for c in cells)), None)
    if hdr is None:
        return False
    try:
        resolve_columns(hdr, SYNONYMS, REQUIRED)
    except Refuse:
        return False
    return True


def _display(brand, schema):
    """C2 (CHARTER v4.3): no brand registry/alias lookup -- brand identity is the label exactly as pasted
    (trimmed/NFC-normalized via T.norm; `schema` param kept only so call sites don't need to change)."""
    return T.norm(brand or "")


def mapping_preview(text):
    lines = T.split_text(text)
    hdr = next((cells for cells in lines[:5] if any(T.fold(c) == "brand" for c in cells)), None)
    if hdr is None:
        raise Refuse("Không tìm thấy dòng header v2 ('Brand')")
    _, preview = resolve_columns(hdr, SYNONYMS, REQUIRED)
    return preview


def parse(lines, add):
    from v4.facts import SCHEMA
    ch, thresholds = SCHEMA["channels"], SCHEMA["thresholds"]
    hdr_i = next((i for i, cells in enumerate(lines[:5]) if any(T.fold(c) == "brand" for c in cells)), None)
    if hdr_i is None:
        raise Refuse("Không tìm thấy dòng header v2 ('Brand')")
    header = lines[hdr_i]
    idx_m, preview = resolve_columns(header, SYNONYMS, REQUIRED)
    idx = {k: v.index for k, v in idx_m.items()}
    add("Cột bắt buộc (v2)", "ok", "Đủ " + str(len(REQUIRED)) + " cột bắt buộc")

    known = {T.fold(ch["total"]): ch["total"], T.fold(ch["affiliate"]): ch["affiliate"],
             T.fold(ch["self_sell"]): ch["self_sell"]}
    known.update({T.fold(c): c for c in ch["self_children"]})
    known.update({T.fold(v): k for k, v in SCHEMA.get("channel_display", {}).items() if k in known.values()})

    data, order, bad, dup, unknown, noname, short_rows = {}, [], 0, 0, set(), 0, 0
    for off, row in enumerate(lines[hdr_i + 1:]):
        ln = hdr_i + 2 + off
        if not any(c.strip() for c in row):
            continue
        if len(row) > len(header) and any(c.strip() for c in row[len(header):]):
            add("Lệch cột (v2)", "fail", f"dòng {ln}: {len(row)} ô nhưng header có {len(header)} cột", row=ln)
            bad += 1
            continue
        short_rows += len(row) < len(header)
        row = row + [""] * (len(header) - len(row))
        brand = _display(row[idx["brand"]], SCHEMA)
        chan = known.get(T.fold(row[idx["channel"]]))
        if not brand:
            noname += 1
            continue
        if chan is None:
            unknown.add(row[idx["channel"]])
            continue
        try:
            plan, ptd, actual = (T.to_int(row[idx[k]]) for k in ("plan", "ptd", "actual"))
            last = T.to_int(row[idx["last"]]) if idx.get("last") is not None else None
        except ValueError as e:
            add("Số liệu (v2)", "fail", f"dòng {ln} ({brand} / {chan}): {e}", row=ln)
            bad += 1
            continue
        if plan is None or ptd is None or actual is None:
            add("Số liệu (v2)", "fail", f"dòng {ln} ({brand} / {chan}): thiếu Plan/GMV plan up to date/Actual", row=ln)
            bad += 1
            continue
        if brand not in data:
            data[brand] = {}
            order.append(brand)
        if chan in data[brand]:
            add("Trùng dòng (v2)", "fail", f"dòng {ln}: {brand} / {chan} bị lặp", row=ln)
            dup += 1
            continue
        x = {}
        for k in ("progress", "gap", "z_col", "mom"):
            i = idx.get(k)
            if i is not None:
                try:
                    x[k] = T.to_int(row[i]) if k == "gap" else T.to_pct(row[i])
                except ValueError:
                    x[k] = None
        data[brand][chan] = {"plan": plan, "ptd": ptd, "actual": actual, "last": last or 0, "line": ln, "x": x}
    if unknown:
        add("Kênh lạ (v2)", "warn", "Bỏ qua kênh không có trong schema: " + ", ".join(sorted(unknown)))
    if noname:
        add("Dòng thiếu Brand (v2)", "warn", f"{noname} dòng không có Brand bị bỏ qua")
    if short_rows:
        add("Dòng ngắn (v2)", "warn", f"{short_rows} dòng có ít ô hơn header")
    if bad or dup:
        raise Refuse(f"{bad + dup} dòng lỗi số liệu/trùng (v2) -- xem checks để biết dòng nào")
    if not data:
        raise Refuse("Không đọc được brand nào (v2)")
    need = [ch["total"], ch["affiliate"], ch["self_sell"], *ch["self_children"]]
    for b in order:
        lack = [c for c in need if c not in data[b]]
        if lack:
            raise Refuse(f"{b}: thiếu kênh {', '.join(lack)} (v2)")
    add("Đủ kênh (v2)", "ok", f"{len(order)} brand × {len(need)} kênh")
    caps = {"has_comparison": False, "has_da": False, "has_channels": True, "has_platforms": False}
    extra = {"cmp_label": None, "suggest": None, "grand_total": None, "k_values": [], "platform": None,
             "caps": caps, "mapping_preview": preview}
    return order, data, extra
