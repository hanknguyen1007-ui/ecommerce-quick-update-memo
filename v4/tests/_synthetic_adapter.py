"""G4 extensibility PROOF fixture (CHARTER v4.1): a synthetic v3-layout VARIANT with renamed/reordered
columns and NO comparison columns. It is a test fixture, not a shipped adapter -- test_extensibility.py
registers it at runtime (registry.register(), the one public extension point) and removes it afterward, to
prove a brand-new layout plugs in without touching base.py, registry.py, v2.py, v3.py or facts.py.

Column renames vs the real v3 layout: "Plan Up to Date" -> "Plan to date", "Total Actual" -> "Actual Total",
"% Required" -> "Run-rate %", "Gap Amount" -> "Gap VND", "% Gap vs Plan" -> "Z %", "% Total Actual" ->
"Progress %" -- and reordered (progress before run-rate). No "<cmp> Actual" / "GMV vs ..." / "DA GMV vs ..."
columns at all, so has_comparison/has_da must come out False (G2 decision 2: hides the dependent line
instead of failing)."""
import re

from core import tsv as T
from v4.adapters.base import Refuse, resolve_columns

NAME = "synthetic_v3_variant"

SYNONYMS = {
    "ptd": [r"^plan to date$"],
    "actual": [r"^actual total$"],
    "gap": [r"^gap vnd$"],
    "zpct": [r"^z\s*%$"],
    "progresspct": [r"^progress\s*%$"],
    "runrate": [r"^run-rate\s*%$"],
}
REQUIRED = {"ptd", "actual", "gap", "zpct", "progresspct", "runrate"}


def sniff(lines):
    return any(any(T.fold(c) == "plan to date" for c in cells) for cells in lines[:12])


def parse(lines, add):
    hdr_i = next((i for i, cells in enumerate(lines[:12]) if any(T.fold(c) == "plan to date" for c in cells)), None)
    if hdr_i is None:
        raise Refuse("Không tìm thấy dòng header synthetic variant ('Plan to date')")
    header = lines[hdr_i]
    idx_m, preview = resolve_columns(header, SYNONYMS, REQUIRED)
    idx = {k: v.index for k, v in idx_m.items()}
    add("Cột bắt buộc (synthetic)", "ok", f"Đủ {len(REQUIRED)} cột bắt buộc; không có cột so sánh (DA/growth)")

    from v4.facts import SCHEMA
    ch = SCHEMA["channels"]
    data, order, bad = {}, [], 0
    for off, row in enumerate(lines[hdr_i + 1:]):
        ln = hdr_i + 2 + off
        if not any(c.strip() for c in row):
            continue
        row = row + [""] * max(0, len(header) - len(row))
        label = row[0].strip()
        if not label:
            continue
        try:
            ptd, actual, gap = (T.to_int(row[idx[k]]) for k in ("ptd", "actual", "gap"))
            rrpct = T.to_pct(row[idx["runrate"]])
        except ValueError as e:
            add("Số liệu (synthetic)", "fail", f"dòng {ln}: {e}", row=ln)
            bad += 1
            continue
        if ptd is None or actual is None or not rrpct:
            bad += 1
            continue
        is_child = label.startswith("↳")
        if is_child:
            label2 = re.sub(r"^↳\s*", "", label)
            fold = T.fold(label2)
            table = {T.fold(ch["affiliate"]): ch["affiliate"], T.fold(ch["self_sell"]): ch["self_sell"],
                     "live": ch["self_children"][0], "video": ch["self_children"][1], "showcase": ch["self_children"][2]}
            chan = table.get(fold)
            if chan is None or not order:
                continue
            brand = order[-1]
        else:
            brand = label
            order.append(brand)
            chan = ch["total"]
        plan_full = round(ptd / (rrpct / 100))
        data.setdefault(brand, {})[chan] = {"plan": plan_full, "ptd": ptd, "actual": actual, "last": 0,
                                            "line": ln, "x": {}}
    if bad:
        raise Refuse(f"{bad} dòng lỗi số liệu (synthetic)")
    need = [ch["total"], ch["affiliate"], ch["self_sell"], *ch["self_children"]]
    for b in order:
        lack = [c for c in need if c not in data.get(b, {})]
        if lack:
            raise Refuse(f"{b}: thiếu kênh {', '.join(lack)} (synthetic)")
    caps = {"has_comparison": False, "has_da": False, "has_channels": True, "has_platforms": False}
    extra = {"cmp_label": None, "suggest": None, "grand_total": None, "k_values": [], "platform": None,
             "caps": caps, "mapping_preview": preview}
    return order, data, extra
