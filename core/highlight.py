"""Highlighter (code, not LLM). Output uses internal inline markup:
   **bold**   ⟦+|text⟧ (green, bold)   ⟦-|text⟧ (red, bold)
Pre-existing **...** (from notes) and ⟦..⟧ (from layout) are preserved and never re-highlighted."""
import re

TOK = re.compile(r"(\*\*.+?\*\*|⟦[+\-]\|.+?⟧)")
_LABELS = r"(?:Động lực|Nguyên nhân|Forecast|Fact vận hành|Điểm nghẽn chung|Điểm nghẽn|Điểm đỡ):"


def _compile(words):
    pats = [
        ("sig", r"(?<![\w.])[+\-]\d[\d,]*(?:\.\d+)?\s?(?:%|pp|[MBK](?!\w))?(?:\s?VNĐ)?"),
        ("money", r"(?<![\w.])\d[\d,]*(?:\.\d+)?[MBK]?\s?VNĐ"),
        ("label", _LABELS),
    ]
    ws = sorted({w for w in words if w}, key=len, reverse=True)
    if ws:
        pats.append(("word", r"(?<!\w)(?:" + "|".join(re.escape(w) for w in ws) + r")(?!\w)"))
    return re.compile("|".join(f"(?P<{n}>{p})" for n, p in pats))


def highlight(text: str, words=(), scope: str = "all") -> str:
    """scope 'all': every signed number gets a green/red marker. 'headline': signed numbers are only bold here;
    layouts add explicit ⟦±|..⟧ markers for the headline numbers (brand Z, EOC%, Overall)."""
    rx = _compile(words)
    out = []
    for seg in TOK.split(text):
        if not seg:
            continue
        if TOK.fullmatch(seg):
            out.append(seg)
            continue
        last = 0
        for m in rx.finditer(seg):
            out.append(seg[last:m.start()])
            tok = m.group(0)
            if m.lastgroup == "sig" and scope == "all":
                out.append(f"⟦{'+' if tok.lstrip()[0] == '+' else '-'}|{tok}⟧")
            else:
                out.append(f"**{tok}**")
            last = m.end()
        out.append(seg[last:])
    return "".join(out)
