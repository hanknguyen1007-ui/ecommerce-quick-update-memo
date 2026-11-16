"""Notes attachment (decision 8 / gate G6, v4.1 charter; rules tightened by C2, v4.3 charter:
NO brand registry/aliases anywhere in the repo). A note line is matched against the brands
PRESENT IN THE CURRENT PASTE ONLY (`brand_order`), never a committed list: case-insensitive, apostrophe-
normalized, ':' separator OPTIONAL. The leading token is found by trying the longest-to-shortest leading
word-run of the line and taking the FIRST length that is a (word-bounded) SUBSTRING of at least one brand
name -- e.g. a note-taker's short "Alpha" matches a longer pasted brand "North Alpha Beauty" because
"Alpha" is CONTAINED IN it. If that run matches more than one brand, or no run up to 6 words matches any, the line
is "unmatched" (G6: never dropped silently -- the UI warns and blocks Copy until acknowledged). typo_fix
.toml's find/replace is applied to the attached fact text (same as the LLM-prose path, reused here)."""
import re

from core.tsv import fold, norm

MAX_TOKEN_WORDS = 6


def _apostrophe(s: str) -> str:
    return s.replace("’", "'").replace("‘", "'")


def apply_typos(text: str, typos: dict) -> str:
    for k, v in (typos or {}).items():
        for a, b in ((k, v), (k[:1].upper() + k[1:], v[:1].upper() + v[1:])):
            text = text.replace(a, b)
    return text


def _contains_word_bounded(haystack: str, needle: str) -> bool:
    if not needle:
        return False
    return re.search(r"(?<!\w)" + re.escape(needle) + r"(?!\w)", haystack) is not None


def _find_brand_token(line: str, brand_order):
    """-> (n_words, [matching brand names]) for the FIRST (longest-to-shortest) leading word-run of `line`
    that is word-bounded-contained in at least one brand's folded name; (0, []) if none up to
    MAX_TOKEN_WORDS. Colon is optional: if present, the text before it is tried FIRST (as one candidate),
    ahead of the plain word-count sweep, so a multi-word brand written with ':' still resolves in one shot."""
    folded_brands = [(fold(_apostrophe(b)), b) for b in brand_order]
    words = line.split()

    def hits_for(candidate: str):
        cf = fold(_apostrophe(candidate.rstrip(":").strip()))
        if not cf:
            return []
        return [b for bf, b in folded_brands if _contains_word_bounded(bf, cf)]

    if ":" in line:
        # a colon is an explicit boundary: only the text before it can be the brand token, never a sweep
        # across words that follow (those are unambiguously part of the fact).
        head = line.split(":", 1)[0]
        return len(head.split()), hits_for(head)

    for n in range(min(len(words), MAX_TOKEN_WORDS), 0, -1):
        h = hits_for(" ".join(words[:n]))
        if h:
            return n, h
    return 0, []


def attach(text: str, brand_order, typos=None) -> dict:
    """-> {"brand": {name: [fact,...]}, "unmatched": [{"line","reason","candidates"}]}. `unmatched` entries
    are NEVER dropped -- the caller (surfaces render / the web UI) warns on them and blocks Copy (G6)."""
    out = {"brand": {}, "unmatched": []}
    for raw in (text or "").replace("\r\n", "\n").split("\n"):
        line = norm(raw)
        if not line or line.startswith("#"):
            continue
        n, hits = _find_brand_token(line, brand_order)
        if len(hits) != 1:
            reason = "không khớp brand nào trong dữ liệu đã dán" if not hits else \
                f"khớp {len(hits)} brand ({', '.join(hits)}) -- không tự chọn"
            out["unmatched"].append({"line": line, "reason": reason, "candidates": hits})
            continue
        brand = hits[0]
        words = line.split()
        rest = " ".join(words[n:]).lstrip()
        if not rest:
            out["unmatched"].append({"line": line, "reason": f"khớp {brand} nhưng không có nội dung fact", "candidates": hits})
            continue
        out["brand"].setdefault(brand, []).append(apply_typos(rest, typos))
    return out
