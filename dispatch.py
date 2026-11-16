"""Single top-level entry point (CHARTER v5.1): sniffs a pasted report and routes it to the right
engine -- the existing campaign pipeline (v4) or the brand-monthly pipeline (v5) -- never guessing
on 0 or 2 matches. This is the ONLY module that imports both v4 and v5; neither engine imports the
other or this module, so campaign stays exactly as it was (G5) and brand-monthly's own 14 locked
decisions are untouched.

build()'s result is a single envelope shape regardless of engine, so the web page (web/index.html)
never special-cases which one ran: {"ok", "engine", "checks", "out": {md,text,html_msg,html_doc},
"ack_required", "warning_messages", "facts"?, "insights"?}. "ack_required"/"warning_messages" are
this module's own normalization of whichever engine produced the result -- v4's own rich `warnings`
dict (ported 1:1 from web/v4/index.html's own `show()`, which built the same list client-side) and
v5's `flags.residual_shift` respectively -- so the "block Copy until acknowledged" behavior is one
rule, tested once, instead of duplicated per engine in JS.
"""
from v4 import pipeline as V4
from v4.adapters import registry as V4R
from v4.adapters.base import Refuse
from v5 import pipeline as V5
from v5.adapters import brand_monthly as V5A
from core import tsv as T


def detect(text):
    """-> "campaign" | "brand-monthly". Refuses on 0 or 2 matches (never guesses)."""
    lines = T.split_text(text)
    is_bm = V5A.sniff(lines)
    is_campaign = V4R.sniff(text)
    if is_bm and is_campaign:
        raise Refuse("Input khớp cả báo cáo campaign và brand-monthly -- không tự chọn, cần làm layout rõ ràng hơn.")
    if is_bm:
        return "brand-monthly"
    if is_campaign:
        return "campaign"
    raise Refuse("Không nhận diện được loại báo cáo (không khớp campaign hay brand-monthly nào đã đăng ký).")


def _campaign_warnings(w):
    """Ported 1:1 from web/v4/index.html's own show(): the same client-side warning-list build,
    moved server-side so it's one tested rule instead of JS duplicated per engine (see module
    docstring). Plain text only (no inline bold) -- the page still escapes/bullets each line."""
    items = []
    if w.get("tp_stale"):
        items.append("Mốc thời gian có thể chưa cập nhật: trùng mốc bản trước nhưng run-rate khác")
    for x in w.get("stale_cols") or []:
        items.append(x["text"])
    for x in w.get("xcheck") or []:
        items.append(f"đối soát cột {x['col']}: {x['rows']} dòng lệch. " + " | ".join(x["examples"]))
    plaus = w.get("plausibility") or []
    if plaus:
        items.append(f"{len(plaus)} dòng MoM không hợp lý: " +
                      "; ".join(f"{p['who']} – {p['why']}" for p in plaus[:3]))
    for u in w.get("notes_unmatched") or []:
        items.append(f'ghi chú chưa gắn vào báo cáo: "{u["line"]}" — {u["reason"]}')
    for c in w.get("checks_warn") or []:
        items.append(c)
    return items


def _brand_monthly_warnings(flags):
    flagged = (flags or {}).get("residual_shift") or []
    if not flagged:
        return []
    return [", ".join(flagged) + " — Livestream giảm mạnh trong khi Showcase&other tăng mạnh cùng "
            "kỳ. Rất có thể Showcase&other đang \"hứng\" phần GMV mà một nguồn khác (ví dụ "
            "Livestream) đang ghi nhận trễ/thiếu, không phải tăng trưởng thật. Kiểm tra lại nguồn "
            "trước khi gửi báo cáo này."]


def build(blocks_text, title="", timepoint="", notes_raw="", prevs=None):
    """blocks_text: list of >=1 pasted textarea blocks, same shape the page already collects for
    campaign's multi-platform input (decision 3). Engine is detected from the FIRST block only
    (v2/v3's own sniff() only looks at that block's first few lines anyway -- concatenating several
    campaign blocks before sniffing would bury a 2nd+ block's own header past where sniff looks);
    brand-monthly's build() then gets every block joined into one paste (its own adapter finds each
    "Date update" section regardless of how the paste was split across textareas)."""
    try:
        engine = detect(blocks_text[0])
    except Refuse as e:
        return {"ok": False, "engine": None, "checks": [{"name": "Input", "status": "fail", "detail": e.reason}]}

    if engine == "brand-monthly":
        r = V5.build("\n".join(blocks_text))
        r["engine"] = "brand-monthly"
        r["ack_required"] = bool(r.get("ok") and _brand_monthly_warnings(r.get("flags")))
        r["warning_messages"] = _brand_monthly_warnings(r.get("flags")) if r.get("ok") else []
        return r

    r = (V4.build(blocks_text[0], title, timepoint, notes_raw, prevs=prevs) if len(blocks_text) == 1
         else V4.build_multi(blocks_text, title, timepoint, notes_raw, prevs=prevs))
    r["engine"] = "campaign"
    msgs = _campaign_warnings(r.get("warnings") or {}) if r.get("ok") else []
    r["warning_messages"] = msgs
    r["ack_required"] = bool(msgs)
    return r
