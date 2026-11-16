"""Synthetic-data builder for the "brand-monthly" preset's own tests. The adapter only ever reads
the rows in config.LABELS (decision 3), so a test fixture needs nothing else -- none of the sheet's
own derived rows/columns a real paste carries (test_no_read.py adds a few back in, deliberately wrong,
to prove that)."""
import calendar

ROWS = ("gmv", "time_runrate", "self_promotion", "affiliate", "ads_gmv",
        "livestream", "video", "showcase", "affiliate_cost", "ads_cost")
_LABEL = {"gmv": "GMV (Total)", "time_runrate": "Time Runrate", "self_promotion": "Self promotion",
          "affiliate": "Affiliate", "ads_gmv": "Shopping Ads GMV", "livestream": "Livestream",
          "video": "Video", "showcase": "Showcase&other", "affiliate_cost": "Cost",
          "ads_cost": "Total_Ads expense"}


def month_str(y, m):
    return f"{y:04d}-{m:02d}"


def make_block(brand, platform, date_update, months, values, extra_rows=()):
    """date_update: (y, m, d). months: [(y, m), ...]. values: {row_key: [n, ...]} aligned with months
    (time_runrate as a fraction 0-1; everything else as int VNĐ). extra_rows: [(label, [cell, ...])]
    appended verbatim (G4: deliberately-wrong derived rows, for test_no_read.py)."""
    y, m, d = date_update
    lines = [f"Date update\t{m}/{d}/{y}\t\t{brand}\t{platform}",
             "\tMonth\t" + "\t".join(month_str(*mm) for mm in months)]
    for key in ROWS:
        cells = values[key]
        if key == "time_runrate":
            cells = [f"{v:.0%}" for v in cells]
        else:
            cells = [str(int(v)) for v in cells]
        lines.append(f"\t{_LABEL[key]}\t" + "\t".join(cells))
    for label, cells in extra_rows:
        lines.append(f"\t{label}\t" + "\t".join(str(c) for c in cells))
    return "\n".join(lines)


def _days(y, m):
    return calendar.monthrange(y, m)[1]


def months_for(cur_y, cur_m, n_before=13):
    """n_before months ending at (cur_y, cur_m), oldest first."""
    out = []
    y, m = cur_y, cur_m
    for _ in range(n_before):
        out.append((y, m))
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    return list(reversed(out))


def valid_values(months, cur_idx, elapsed_day, gmv_day=10_000_000, sp_share=0.7, ls_share=0.4,
                  video_share=0.02, aff_cost_rate=0.1, ads_cost_rate=0.06, ads_share=0.5):
    """A fully self-consistent raw series (every decision-5 integrity assert holds) sized by a flat
    per-day GMV run-rate, full days for every month except a 0 (future) tail after cur_idx."""
    n = len(months)
    gmv, runrate, sp, aff, ads, ls, vid, sc, ac, adc = ([0] * n for _ in range(10))
    for i, (y, m) in enumerate(months):
        if i > cur_idx:
            continue
        days = elapsed_day if i == cur_idx else _days(y, m)
        full_days = _days(y, m)
        g = gmv_day * days
        gmv[i] = g
        runrate[i] = days / full_days
        s = round(g * sp_share)
        a = g - s
        sp[i], aff[i] = s, a
        adgmv = round(g * ads_share)
        ads[i] = adgmv
        l_ = round(s * ls_share)
        v_ = round(s * video_share)
        ls[i], vid[i] = l_, v_
        sc[i] = s - l_ - v_
        ac[i] = round(a * aff_cost_rate)
        adc[i] = round(adgmv * ads_cost_rate)
    return {"gmv": gmv, "time_runrate": runrate, "self_promotion": sp, "affiliate": aff, "ads_gmv": ads,
            "livestream": ls, "video": vid, "showcase": sc, "affiliate_cost": ac, "ads_cost": adc}
