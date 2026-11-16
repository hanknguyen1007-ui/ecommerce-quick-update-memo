"""Blocks -> md / plain text / HTML (messenger | doc). Blocks: {"t": h1|h2|li|p|hr, "l": level, "s": inline-markup text}."""
import html
import re

TOK = re.compile(r"\*\*(.+?)\*\*|⟦([+\-])\|(.+?)⟧")
GREEN, RED = "#188038", "#d93025"
EMO = {"+": "🟢", "-": "🔴"}


def inline(s: str, mode: str) -> str:
    """mode: md | text | msg | doc"""
    out, last = [], 0
    esc = (lambda x: html.escape(x, quote=False)) if mode in ("msg", "doc") else (lambda x: x)
    for m in TOK.finditer(s):
        out.append(esc(s[last:m.start()]))
        last = m.end()
        if m.group(1) is not None:
            b = m.group(1)
            out.append({"md": f"**{b}**", "text": b, "msg": f"<b>{esc(b)}</b>", "doc": f"<b>{esc(b)}</b>"}[mode])
        else:
            sg, t = m.group(2), f"{EMO[m.group(2)]} {m.group(3)}"
            col = GREEN if sg == "+" else RED
            out.append({"md": f"**{t}**", "text": t, "msg": f"<b>{esc(t)}</b>",
                        "doc": f'<b><span style="color:{col}">{esc(t)}</span></b>'}[mode])
    out.append(esc(s[last:]))
    return "".join(out)


def plain_of(s: str) -> str:
    return inline(s, "text")


def to_md(blocks, mode="md") -> str:
    lines = []
    for b in blocks:
        s = inline(b.get("s", ""), mode)
        t = b["t"]
        if t == "h1":
            lines += [("# " if mode == "md" else "") + s, ""]
        elif t == "h2":
            lines += ["", ("## " if mode == "md" else "") + s]
        elif t == "li":  # '➔' lines carry their own marker: no extra bullet ("• ➔" looks wrong in Lark)
            lines.append("  " * b["l"] + ("" if b["s"].startswith("➔") else "- ") + s)
        elif t == "hr":
            lines += ["", "---"]
        else:
            lines.append(s)
    return "\n".join(lines).strip() + "\n"


def to_text(blocks) -> str:
    return to_md(blocks, "text")


def _tree(blocks):
    """Group consecutive li blocks into nested lists."""
    root, stack = [], []
    for b in blocks:
        if b["t"] != "li" or b["s"].startswith("➔"):  # arrow lines render as plain paragraphs, never <li>
            stack = []
            root.append(("blk", b))
            continue
        node = {"b": b, "kids": []}
        while stack and stack[-1][0] >= b["l"]:
            stack.pop()
        if stack:
            stack[-1][1]["kids"].append(node)
        else:
            root.append(("li", node))
        stack.append((b["l"], node))
    return root


def _ul(nodes, mode):
    items = []
    for n in nodes:
        kids = _ul(n["kids"], mode) if n["kids"] else ""
        items.append(f"<li>{inline(n['b']['s'], mode)}{kids}</li>")
    return "<ul>" + "".join(items) + "</ul>"


def to_html(blocks, mode="doc") -> str:
    out, run = [], []

    def flush():
        nonlocal run
        if run:
            out.append(_ul(run, mode))
            run = []

    for kind, x in _tree(blocks):
        if kind == "li":
            run.append(x)
            continue
        flush()
        t, s = x["t"], inline(x.get("s", ""), mode)
        if t in ("h1", "h2"):
            out.append(f"<p><b>{s}</b></p>")
        elif t == "hr":
            out.append("<hr>")
        else:
            out.append(f"<p>{s}</p>")
    flush()
    return "".join(out)
