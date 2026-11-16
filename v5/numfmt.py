"""Number formatting for the "brand-monthly" preset. Reuses core.numfmt's exact-arithmetic rounding
(Fraction + ROUND_HALF_UP) but with a Unicode minus sign (U+2212), per the golden file -- core.numfmt
itself stays untouched (ASCII '-') because the campaign engine's own golden output depends on that.
"""
from fractions import Fraction

from core import numfmt as N
from core.numfmt import _q  # noqa: F401 -- exact Decimal rounding, reused rather than duplicated


def money(n, signed=False) -> str:
    return N.short(n, signed=signed).replace("-", "−")


def money_m(n, signed=False) -> str:
    """DA/delta money is always shown in M (never auto-scaled to K/B), per the golden file."""
    sign = ("-" if n < 0 else ("+" if signed and n > 0 else ""))
    return f"{sign}{_q(Fraction(abs(n)) / 10**6, 1)}M".replace("-", "−")


def money_b(n) -> str:
    return f"{_q(Fraction(abs(n)) / 10**9, 2)}B"


def pct(ratio, nd=1, signed=False, unit="%") -> str:
    return N.pct(ratio, nd, signed=signed, unit=unit).replace("-", "−")


def ratio(x, nd=2) -> str:
    return str(_q(Fraction(x), nd))
