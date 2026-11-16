"""Quick insights (decision 7, tightened by CHARTER v4.2's H4): fixed sentence templates filled from
facts, nothing inferred or guessed (FORBIDDEN: hypotheses/inferred causes/recommendations). Each insight
declares the exact facts paths it reads (`uses`) so G1 ("every number traces to facts") can be checked
mechanically, and is skipped entirely -- not fabricated -- when its required facts are absent (decision 2).

H4: an insight must add information the report TEXT does not already state -- never restate overall
progress, the forecast, or the single best/worst brand (surfaces.text.render() already prints all three).
Both templates below are portfolio-wide AGGREGATES the main report never computes at all:
  - the one net-negative channel across every brand combined (channels_x), plus which single brand-cell
    drives it -- the report only ever shows per-brand channel gaps, never this cross-brand channel total.
  - how DA's sign splits across brands, weighted by plan share -- the report only shows DA per brand/
    channel/overall, never this portfolio-wide spread.
"""
from core import numfmt as N


def _net_negative_channel(f):
    leaves = [c for c in f.get("disp", {}) if c in f.get("channels_x", {})]
    neg = [c for c in leaves if f["channels_x"][c]["gap"] < 0]
    if len(neg) != 1:
        return None  # only meaningful when exactly one channel is net-negative; ambiguous otherwise
    c = neg[0]
    xg = f["channels_x"][c]
    cells = [(b, f["brands"][b]["channels"][c]) for b in f["brand_order"] if c in f["brands"][b]["channels"]]
    if not cells:
        return None
    worst_b, worst_ce = min(cells, key=lambda x: x[1]["gap"])
    if worst_ce["gap"] >= 0:
        return None
    name = f["disp"].get(c, c)
    return {"id": "net_negative_channel",
            "uses": ["channels_x.*.gap", "channels_x.*.gap_abs_s", "brands.*.channels.*.gap",
                      "brands.*.channels.*.gap_abs_s"],
            "text": f"{name} là kênh âm ròng duy nhất toàn danh mục (hụt {xg['gap_abs_s']} VNĐ); "
                    f"hụt lớn nhất tại {worst_b} (hụt {worst_ce['gap_abs_s']} VNĐ)."}


def _da_sign_spread(f):
    if not f.get("caps", {}).get("has_da"):
        return None
    order = f["brand_order"]
    das = [(b, f["brands"][b].get("da_pct")) for b in order]
    if not order or any(d is None for _, d in das):
        return None
    neg = [b for b, d in das if d < 0]
    if not neg or len(neg) == len(order):
        return None  # not a "spread" when every brand (or none) agrees in sign
    share = sum(f["brands"][b]["contribution"] for b in neg)
    return {"id": "da_sign_spread", "uses": ["caps.has_da", "brands.*.da_pct", "brands.*.contribution"],
            "text": f"Tăng trưởng DA âm tại {len(neg)}/{len(order)} brand, chiếm {N.pct(share, 1)} "
                    f"plan toàn danh mục."}


TEMPLATES = (_net_negative_channel, _da_sign_spread)


def generate(facts: dict) -> list:
    """-> [{"id","uses","text"}, ...] -- only the templates whose required facts are present AND whose
    condition actually holds (e.g. "exactly one negative channel") fire."""
    out = []
    for tpl in TEMPLATES:
        r = tpl(facts)
        if r is not None:
            out.append(r)
    return out
