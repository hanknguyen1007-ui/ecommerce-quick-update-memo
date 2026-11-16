"""Entry point for the "brand-monthly" preset (CHARTER v5): the only module that sees both the
adapter and facts/surfaces, mirroring v4/pipeline.py's own shape (decision 1) without touching it."""
from v4.adapters.base import Refuse
from v5 import facts as F
from v5 import render as R
from v5.adapters import brand_monthly as A
from v5.surfaces import text as TEXT


def build(text):
    """-> {"ok", "checks", "facts", "out": {md, text, html_msg, html_doc}, "flags"} or
    {"ok": False, "checks": [...]} on refusal."""
    checks = []
    try:
        blocks = A.parse(text)
    except Refuse as e:
        return {"ok": False, "checks": [{"name": "Input", "status": "fail", "detail": e.reason}]}
    try:
        facts = F.compute(blocks)
    except Refuse as e:
        return {"ok": False, "checks": [{"name": "Facts", "status": "fail", "detail": e.reason}]}
    checks.append({"name": "Input", "status": "ok", "detail": f"{len(blocks)} platform block(s)"})
    recap_blocks, full_blocks = TEXT.render(facts)
    flags = {"residual_shift": [p["name"] for p in facts["platforms"] if p["flags"]["residual_shift"]]}
    return {
        "ok": True, "checks": checks, "facts": facts,
        "out": {
            "md": R.to_md(full_blocks), "text": R.to_text(full_blocks),
            "html_msg": R.to_html(recap_blocks), "html_doc": R.to_html(full_blocks),
        },
        "flags": flags,
    }
