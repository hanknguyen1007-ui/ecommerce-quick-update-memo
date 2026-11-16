"""blocks -> markdown / plain text / HTML, for the "brand-monthly" preset only.

Deliberately NOT core/render.py: that module's to_html() maps h1/h2 to a bold <p>, never a real
heading tag, and CHARTER v5 (rule 14) requires true H2/H3 for Lark Docs -- changing core/render.py's
h1/h2 mapping would change the campaign engine's own doc.html byte-for-byte (G5 forbids that). A
second, preset-scoped renderer is cheaper and safer than teaching one shared renderer two unrelated
heading conventions.

Block dict: {"type": "p" | "h2" | "h3" | "hr" | "li" | "li2", "text": str, "break": bool}. "text"
already carries **bold** markup and any literal emoji/unicode-minus. A "li"/"li2" with "break": True
(set on the block's own "➔" headline line, and on the "Quick recap"/"Highlights"/"Lowlights" labels)
always starts its OWN new paragraph (a blank line before it, even mid-list) but still joins directly
into whatever plain bullets follow it, with no bullet marker of its own -- ported 1:1 from
core/render.py's "➔" special-case, just re-implemented here instead of shared (see module docstring).
"""
import html
import re

_BOLD = re.compile(r"\*\*(.+?)\*\*")


def _inline_text(s: str) -> str:
    return _BOLD.sub(lambda m: m.group(1), s)


def _inline_html(s: str) -> str:
    out, last = [], 0
    for m in _BOLD.finditer(s):
        out.append(html.escape(s[last:m.start()], quote=False))
        out.append(f"<b>{html.escape(m.group(1), quote=False)}</b>")
        last = m.end()
    out.append(html.escape(s[last:], quote=False))
    return "".join(out)


def _is_break(b):
    return b["type"] in ("li", "li2") and (b["text"].startswith("➔") or b.get("break"))


def _md_like(blocks, render_text):
    """"merge_up": True (the lens takeaway, right after its "### " heading) joins the previous
    segment with a single newline instead of starting a new, blank-separated one -- a markdown/text
    only concern (to_html doesn't need it: <h3> next to <p> needs no blank line between them)."""
    segments, cur = [], []
    for b in blocks:
        t, s = b["type"], render_text(b["text"])
        if t in ("li", "li2"):
            if _is_break(b) and cur:
                segments.append("\n".join(cur))
                cur = []
            prefix = "" if _is_break(b) else ("   * " if t == "li2" else "* ")
            cur.append(prefix + s)
            continue
        if cur:
            segments.append("\n".join(cur))
            cur = []
        rendered = s if t not in ("h2", "h3", "hr") else {"h2": "## " + s, "h3": "### " + s, "hr": "---"}[t]
        if b.get("merge_up") and segments:
            segments[-1] += "\n" + rendered
        else:
            segments.append(rendered)
    if cur:
        segments.append("\n".join(cur))
    return "\n\n".join(segments) + "\n"


def to_md(blocks) -> str:
    return _md_like(blocks, lambda s: s)


def to_text(blocks) -> str:
    return _md_like(blocks, _inline_text)


def to_html(blocks) -> str:
    out, ul = [], []  # ul: list of (li_html, [nested li2_html, ...])

    def flush():
        if not ul:
            return
        items = []
        for li_html, kids in ul:
            nested = f"<ul>{''.join(f'<li>{k}</li>' for k in kids)}</ul>" if kids else ""
            items.append(f"<li>{li_html}{nested}</li>")
        out.append("<ul>" + "".join(items) + "</ul>")
        ul.clear()

    for b in blocks:
        t, s = b["type"], b["text"]
        if t == "li2":
            if ul:
                ul[-1][1].append(_inline_html(s))
            continue
        if t == "li":
            if _is_break(b):
                flush()
                out.append(f"<p>{_inline_html(s)}</p>")
            else:
                ul.append((_inline_html(s), []))
            continue
        flush()
        if t == "h2":
            out.append(f"<h2>{html.escape(s, quote=False)}</h2>")
        elif t == "h3":
            out.append(f"<h3>{html.escape(s, quote=False)}</h3>")
        elif t == "hr":
            out.append("<hr>")
        else:
            out.append(f"<p>{_inline_html(s)}</p>")
    flush()
    return "".join(out)
