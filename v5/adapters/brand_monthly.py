"""Adapter for CHARTER v5's "brand-monthly" preset: a wide monthly building-block sheet, 1-2 platform
blocks (Shopee/TikTok) pasted together, each starting at its own "Date update" row.

Turns pasted text into a list of per-platform dicts:
    {"brand": str, "platform": "shopee"|"tiktok", "date_update": date, "months": [(y, m), ...],
     "raw": {metric: [int|float, ...]}}   # raw[metric][i] aligned with months[i]

Never reads a derived row (decision 3): only the 9 raw metrics in config LABELS, plus "month" for the
time axis and "date update" for the block header. Refuses (v4.adapters.base.Refuse, reused rather than
duplicated -- this reads campaign code, it does not edit it) on anything it cannot safely parse: no
guessing, matching v4's own adapter contract (decision 1, "surfaces/adapters never guess").
"""
import datetime

from core import tsv as T
from v4.adapters.base import Refuse
from v5 import config as C

NAME = "brand-monthly"

_METRICS = [k for k in C.LABELS if k not in ("date_update", "month")]


def sniff(lines):
    return any(len(r) > 0 and T.fold(r[0]) == C.LABELS["date_update"] for r in lines)


def _block_spans(lines):
    starts = [i for i, r in enumerate(lines) if len(r) > 0 and T.fold(r[0]) == C.LABELS["date_update"]]
    if not starts:
        raise Refuse("Không tìm thấy dòng 'Date update' -- không nhận diện được layout brand-monthly.")
    spans = []
    for n, s in enumerate(starts):
        e = starts[n + 1] if n + 1 < len(starts) else len(lines)
        spans.append((s, e))
    return spans


def _parse_header(row, line_no):
    if len(row) < 5:
        raise Refuse(f"Dòng {line_no} 'Date update' thiếu cột (cần date/brand/platform).")
    try:
        d = datetime.datetime.strptime(row[1].strip(), "%m/%d/%Y").date()
    except ValueError:
        raise Refuse(f"Dòng {line_no}: không đọc được ngày 'Date update' ({row[1]!r}).")
    brand = row[3].strip()
    platform_raw = row[4].strip()
    if not brand:
        raise Refuse(f"Dòng {line_no}: thiếu tên brand.")
    if not platform_raw:
        raise Refuse(f"Dòng {line_no}: thiếu tên platform.")
    return d, brand, platform_raw


def _canon_platform(platform_raw):
    folded = T.fold(platform_raw)
    for key in C.PLATFORM_ORDER:
        if C.PLATFORMS[key]["sniff"] in folded:
            return key
    raise Refuse(f"Platform không nhận diện: {platform_raw!r} (chỉ hỗ trợ: {', '.join(C.PLATFORM_ORDER)}).")


def _parse_months(cells, line_no):
    out = []
    for c in cells:
        c = c.strip()
        if not c:
            break
        try:
            y, m = c.split("-")
            out.append((int(y), int(m)))
        except ValueError:
            raise Refuse(f"Dòng {line_no}: không đọc được cột tháng ({c!r}).")
    if not out:
        raise Refuse(f"Dòng {line_no}: dòng 'Month' rỗng.")
    return out


def _parse_metric_row(key, cells, n_months, line_no):
    is_pct = key == "time_runrate"
    out = []
    for i in range(n_months):
        raw = cells[i] if i < len(cells) else ""
        try:
            if is_pct:
                v = T.to_pct(raw)
                out.append((v / 100.0) if v is not None else 0.0)
            else:
                v = T.to_int(raw)
                out.append(v if v is not None else 0)
        except ValueError:
            raise Refuse(f"Dòng {line_no}: không đọc được giá trị ({raw!r}) cho '{key}'.")
    return out


def _parse_block(lines, start, end):
    header_line = start + 1
    date_update, brand, platform_raw = _parse_header(lines[start], header_line)
    months = None
    found = {}
    for i in range(start + 1, end):
        row = lines[i]
        if len(row) < 2 or not row[1].strip():
            continue
        label = T.fold(row[1])
        line_no = i + 1
        if label == C.LABELS["month"] and months is None:
            months = _parse_months(row[2:], line_no)
            continue
        for key in _METRICS:
            if label != C.LABELS[key]:
                continue
            if key in found:
                break  # decision 2: the sheet repeats some raw rows verbatim -- first occurrence wins
            if months is None:
                raise Refuse(f"Dòng {line_no}: gặp '{row[1]}' trước khi có dòng 'Month'.")
            found[key] = _parse_metric_row(key, row[2:], len(months), line_no)
            break
    if months is None:
        raise Refuse(f"Khối bắt đầu dòng {header_line}: thiếu dòng 'Month'.")
    missing = [k for k in _METRICS if k not in found]
    if missing:
        raise Refuse(f"Khối bắt đầu dòng {header_line}: thiếu cột bắt buộc: {', '.join(missing)}.")
    platform = _canon_platform(platform_raw)
    return {"brand": brand, "platform": platform, "date_update": date_update,
            "months": months, "raw": found}


def parse(text):
    lines = T.split_text(text)
    blocks = [_parse_block(lines, s, e) for s, e in _block_spans(lines)]
    brands = {T.fold(b["brand"]) for b in blocks}
    if len(brands) > 1:
        names = ", ".join(sorted({b["brand"] for b in blocks}))
        raise Refuse(f"Các khối platform có brand khác nhau ({names}) -- không tự gộp.")
    platforms = [b["platform"] for b in blocks]
    if len(platforms) != len(set(platforms)):
        raise Refuse("Hai khối trong cùng một paste trùng platform -- không nhận diện được đâu là khối nào.")
    order = {k: i for i, k in enumerate(C.PLATFORM_ORDER)}
    blocks.sort(key=lambda b: order[b["platform"]])
    return blocks
