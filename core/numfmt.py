"""Deterministic number formatting. Exact arithmetic (Fraction) + ROUND_HALF_UP. ASCII '-' for negatives."""
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction


def _q(x: Fraction, nd: int) -> Decimal:
    d = Decimal(x.numerator) / Decimal(x.denominator)
    return d.quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_UP)


def rnd(x) -> int:
    """Round half up to int (Python's round() is banker's)."""
    x = Fraction(x)
    return (2 * x.numerator + x.denominator) // (2 * x.denominator)


def _sign(v: Decimal | int, signed: bool) -> str:
    if v < 0:
        return "-"
    return "+" if signed and v > 0 else ""


def full(n: int, signed: bool = False) -> str:
    return f"{_sign(n, signed)}{abs(int(n)):,}"


def short(n: int, signed: bool = False, nd_m: int = 1, nd_b: int = 2, nd_k: int = 1) -> str:
    """Brand/channel level: B / M / K with fixed decimals."""
    a = abs(int(n))
    if a >= 10**9:
        v, u = _q(Fraction(a, 10**9), nd_b), "B"
    elif a >= 10**6:
        v, u = _q(Fraction(a, 10**6), nd_m), "M"
    elif a >= 10**3:
        v, u = _q(Fraction(a, 10**3), nd_k), "K"
    else:
        return f"{_sign(n, signed)}{a}"
    return f"{_sign(n, signed)}{v}{u}"


def short_b1(n: int) -> str:
    """Overall '~3.7B' helper."""
    return f"{_q(Fraction(abs(int(n)), 10**9), 1)}B"


def pct(ratio, nd: int, signed: bool = False, unit: str = "%") -> str:
    """ratio is a fraction (0.4419 -> '44.19%'). pp uses unit='pp' on a difference of fractions."""
    v = _q(Fraction(ratio) * 100, nd)
    return f"{_sign(v, signed)}{abs(v)}{unit}"
