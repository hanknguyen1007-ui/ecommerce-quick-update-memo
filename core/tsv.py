"""Excel-clipboard TSV parsing + Vietnamese/Excel number parsing."""
import csv
import io
import re
import unicodedata


def norm(s: str) -> str:
    return unicodedata.normalize("NFC", s).replace(" ", " ").strip()


def fold(s: str) -> str:
    return norm(s).casefold()


def _unquote(c: str) -> str:
    c = c.strip()
    return c[1:-1].replace('""', '"') if len(c) >= 2 and c[0] == c[-1] == '"' else c


def split_line(ln: str):
    """One TSV line -> normalized cells (strict TAB split, no csv quoting)."""
    return [norm(_unquote(c)) for c in ln.split("\t")]


def split_text(text: str):
    """Raw pasted block -> list of per-line cell lists, 0-indexed (line N is out[N-1]). No blank-line skipping."""
    text = text.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n")
    return [split_line(ln) for ln in text.split("\n")]


def parse_table(text: str):
    """-> (header, rows, line_numbers). Blank rows skipped; line numbers are 1-based incl. header.
    Split strictly on TAB per line (no csv quoting): empty / '—' cells keep their column position, and a stray
    quote character can never swallow following tabs or lines."""
    out, lines = [], []
    for i, r in enumerate(split_text(text), start=1):
        if any(c.strip() for c in r):
            out.append(r)
            lines.append(i)
    if not out:
        return [], [], []
    return out[0], out[1:], lines[1:]


_DASH = {"", "-", "—", "–", "n/a", "na"}
_VN_DOTS = re.compile(r"^-?\d{1,3}(\.\d{3})+$")


def to_int(s: str):
    """'1,234,567' / '1.234.567' / '-114,665,928' -> int; blank/dash -> None; garbage -> ValueError."""
    s = norm(s).replace("−", "-").replace(" ", "")
    if s.lower() in _DASH:
        return None
    if _VN_DOTS.match(s):
        s = s.replace(".", "")
    s = s.replace(",", "")
    if not re.fullmatch(r"-?\d+(\.0+)?", s):
        raise ValueError(f"không phải số nguyên: {s!r}")
    return int(float(s)) if "." in s else int(s)


def to_pct(s: str):
    """'+3.19%' / '-5.28%' / '—' -> float percent value (3.19) or None."""
    s = norm(s).replace("−", "-").replace("%", "").replace("+", "").replace(" ", "")
    if s.lower() in _DASH:
        return None
    # locale: '-82,4' (VN decimal comma) must not become -824; '1.234,5' / '1,234.5' -> the LAST separator is the decimal
    if "," in s and "." in s:
        dec = "," if s.rfind(",") > s.rfind(".") else "."
        s = s.replace("." if dec == "," else ",", "").replace(dec, ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        raise ValueError(f"không phải %: {s!r}")
