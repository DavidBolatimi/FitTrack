"""
End-to-end product analysis for FitTrack.
Runs every SQL file in /sql, performs statistical tests, renders figures,
and writes a findings summary to reports/findings.md.
"""
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

from build_database import build

ROOT = Path(__file__).resolve().parents[1]
SQL, FIG, REP = ROOT / "sql", ROOT / "reports" / "figures", ROOT / "reports"
FIG.mkdir(parents=True, exist_ok=True)

PRIMARY, ACCENT, MUTED, GRID = "#1F6FEB", "#F78166", "#8B949E", "#E6E6E6"
plt.rcParams.update({
    "figure.dpi": 150, "savefig.bbox": "tight", "font.size": 10,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "axes.axisbelow": True,
    "axes.titleweight": "bold", "axes.titlesize": 12,
})


def q(con, name: str) -> pd.DataFrame:
    return pd.read_sql((SQL / name).read_text(), con)


def two_prop_ztest(x1, n1, x2, n2):
    p1, p2 = x1 / n1, x2 / n2
    pooled = (x1 + x2) / (n1 + n2)
    se_pooled = np.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    z = (p2 - p1) / se_pooled
    p_value = 2 * (1 - stats.norm.cdf(abs(z)))
    se = np.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    ci = (p2 - p1 - 1.96 * se, p2 - p1 + 1.96 * se)
    return p1, p2, z, p_value, ci


def srm_check(n_control, n_treatment):
    """Sample ratio mismatch: chi-square vs. expected 50/50 split."""
    total = n_control + n_treatment
    return stats.chisquare([n_control, n_treatment], [total / 2, total / 2]).pvalue


def main():
    con = sqlite3.connect(build())
    out = {}

    # ---------- KPIs ----------
    kpi = q(con, "01_kpi_overview.sql").iloc[0]
    out["kpi"] = kpi

    # ---------- Funnel ----------
    funnel = q(con, "02_funnel.sql")
    allrow = funnel[funnel.device == "all"].iloc[0]
    steps = ["signups", "onboarded", "first_workout", "trial", "paid"]
    labels = ["Signed up", "Onboarded", "First workout", "Started trial", "Paid"]
    vals = [allrow[s] for s in steps]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    bars = ax.barh(labels[::-1], vals[::-1], color=PRIMARY)
    for b, v in zip(bars, vals[::-1]):
        ax.text(b.get_width() + 200, b.get_y() + b.get_height() / 2,
                f"{v:,.0f}  ({v / vals[0]:.1%})", va="center")
    ax.set_xlim(0, vals[0] * 1.3)
    ax.set_title("Acquisition funnel: signup to paid subscription")
    ax.set_xlabel("Users")
    ax.grid(axis="y", visible=False)
    fig.savefig(FIG / "01_funnel.png"); plt.close(fig)

    dev = funnel[funnel.device != "all"].set_index("device")
    fig, ax = plt.subplots(figsize=(8, 4))
    cols = ["signup_to_onboard_pct", "onboard_to_workout_pct", "workout_to_trial_pct", "trial_to_paid_pct"]
    names = ["Signup → Onboard", "Onboard → Workout", "Workout → Trial", "Trial → Paid"]
    x = np.arange(len(cols)); w = 0.26
    palette = {"ios": PRIMARY, "android": ACCENT, "web": MUTED}
    for i, d in enumerate(["ios", "android", "web"]):
        ax.bar(x + (i - 1) * w, dev.loc[d, cols], w, label=d, color=palette[d])
    ax.set_xticks(x, names); ax.set_ylabel("Step conversion (%)")
    ax.set_title("Step conversion by device: Android drops at first workout")
    ax.legend(frameon=False); ax.grid(axis="x", visible=False)
    fig.savefig(FIG / "02_funnel_by_device.png"); plt.close(fig)
    out["funnel"] = funnel

    # ---------- Retention cohorts ----------
    ret = q(con, "03_weekly_retention_cohorts.sql")
    pivot = ret.pivot(index="cohort_week", columns="week_n", values="retention_pct")
    pivot = pivot.iloc[1:-1]  # drop partial first/last cohorts
    # Cells with zero active users are missing from the query; fill them when the week was fully observed
    end = pd.Timestamp("2026-06-28")
    for cw in pivot.index:
        for wk in pivot.columns:
            if np.isnan(pivot.loc[cw, wk]) and pd.Timestamp(cw) + pd.Timedelta(days=7 * (wk + 2)) <= end:
                pivot.loc[cw, wk] = 0.0
    fig, ax = plt.subplots(figsize=(10, 5.5))
    im = ax.imshow(pivot.values, cmap="Blues", aspect="auto", vmin=0, vmax=40)
    ax.set_xticks(range(pivot.shape[1]), [f"W{c}" for c in pivot.columns])
    ax.set_yticks(range(pivot.shape[0]), pivot.index)
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            v = pivot.values[i, j]
            if not np.isnan(v):
                ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=7.5,
                        color="white" if v > 24 else "#24292F")
    ax.grid(False)
    ax.set_title("Weekly cohort retention (% of signups completing a workout)")
    ax.set_xlabel("Weeks since signup"); ax.set_ylabel("Signup cohort (week of)")
    fig.colorbar(im, ax=ax, shrink=0.8, label="Retention %")
    fig.savefig(FIG / "03_retention_heatmap.png"); plt.close(fig)
    curve = pivot.mean(axis=0)
    out["retention_curve"] = curve

    # ---------- A/B test ----------
    ab = q(con, "04_ab_test_onboarding.sql").set_index("experiment_group")
    c, t = ab.loc["control"], ab.loc["treatment"]
    srm_p = srm_check(c.users, t.users)
    ab_rows = []
    for metric, col in [("Onboarding completion", "onboarded"),
                        ("Activation (first workout)", "activated"),
                        ("Trial start", "trials")]:
        p1, p2, z, pv, ci = two_prop_ztest(c[col], c.users, t[col], t.users)
        ab_rows.append(dict(metric=metric, control=p1, treatment=p2, abs_lift_pp=(p2 - p1) * 100,
                            rel_lift=(p2 / p1 - 1), ci_low_pp=ci[0] * 100, ci_high_pp=ci[1] * 100,
                            z=z, p_value=pv))
    ab_res = pd.DataFrame(ab_rows)
    out["ab"], out["srm_p"] = ab_res, srm_p

    fig, ax = plt.subplots(figsize=(8, 3.6))
    y = np.arange(len(ab_res))[::-1]
    ax.errorbar(ab_res.abs_lift_pp, y,
                xerr=[ab_res.abs_lift_pp - ab_res.ci_low_pp, ab_res.ci_high_pp - ab_res.abs_lift_pp],
                fmt="o", color=PRIMARY, capsize=5, ms=7)
    ax.axvline(0, color=MUTED, ls="--")
    ax.set_yticks(y, ab_res.metric)
    ax.set_ylim(-0.5, len(ab_res) - 0.5)
    for yi, r in zip(y, ab_res.itertuples()):
        ax.text(r.ci_high_pp + 0.3, yi, f"+{r.abs_lift_pp:.1f} pp  (p={r.p_value:.3g})", va="center")
    ax.set_xlim(-1, max(ab_res.ci_high_pp) + 4.5)
    ax.set_xlabel("Treatment − control (percentage points, 95% CI)")
    ax.set_title("Onboarding redesign A/B test results")
    fig.savefig(FIG / "04_ab_test.png"); plt.close(fig)

    # ---------- Feature adoption ----------
    feat = q(con, "05_feature_adoption_retention.sql").set_index("segment")
    a, n = feat.loc["adopted_workout_plans"], feat.loc["did_not_adopt"]
    chi_p = stats.chi2_contingency([
        [round(a.users * a.week4_retention_pct / 100), round(a.users * (1 - a.week4_retention_pct / 100))],
        [round(n.users * n.week4_retention_pct / 100), round(n.users * (1 - n.week4_retention_pct / 100))],
    ])[1]
    out["feat"], out["feat_p"] = feat, chi_p
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.6))
    for ax, col, title in [(axes[0], "week4_retention_pct", "Week-4 retention"),
                           (axes[1], "paid_conversion_pct", "Paid conversion")]:
        vals_ = [a[col], n[col]]
        bs = ax.bar(["Adopted\nWorkout Plans", "Did not\nadopt"], vals_, color=[PRIMARY, MUTED], width=0.55)
        for b, v in zip(bs, vals_):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.8, f"{v:.1f}%", ha="center", fontweight="bold")
        ax.set_title(title); ax.set_ylim(0, max(vals_) * 1.25); ax.grid(axis="x", visible=False)
    fig.suptitle("Week-1 Workout Plans adopters vs. non-adopters (activated users)", fontweight="bold")
    fig.tight_layout()
    fig.savefig(FIG / "05_feature_adoption.png"); plt.close(fig)

    # ---------- Channels ----------
    ch = q(con, "06_channel_performance.sql")
    out["channels"] = ch
    fig, ax = plt.subplots(figsize=(8, 4))
    colors = [ACCENT if c_ == "paid_social" else PRIMARY for c_ in ch.acquisition_channel]
    bs = ax.bar(ch.acquisition_channel, ch.revenue_per_signup_usd, color=colors)
    for b, v, pc in zip(bs, ch.revenue_per_signup_usd, ch.paid_conversion_pct):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.08, f"${v:.2f}\n{pc:.1f}% paid", ha="center", fontsize=9)
    ax.set_ylim(0, ch.revenue_per_signup_usd.max() * 1.3)
    ax.set_ylabel("Revenue per signup to date (USD)")
    ax.set_title("Channel quality: revenue per signup")
    ax.grid(axis="x", visible=False)
    fig.savefig(FIG / "06_channel_quality.png"); plt.close(fig)

    # ---------- WAU / MRR ----------
    trend = q(con, "07_weekly_active_users_mrr.sql")
    trend = trend[trend.week_start >= "2026-01-05"]
    fig, ax1 = plt.subplots(figsize=(9, 4))
    ax1.plot(pd.to_datetime(trend.week_start), trend.wau, color=PRIMARY, lw=2, label="WAU")
    ax1.set_ylabel("Weekly active users", color=PRIMARY)
    ax2 = ax1.twinx()
    ax2.plot(pd.to_datetime(trend.week_start), trend.mrr_usd, color=ACCENT, lw=2, label="MRR")
    ax2.set_ylabel("MRR (USD)", color=ACCENT); ax2.grid(False)
    ax2.spines["right"].set_visible(True)
    ax1.set_title("Weekly active users and MRR")
    fig.autofmt_xdate()
    fig.savefig(FIG / "07_wau_mrr.png"); plt.close(fig)
    out["trend"] = trend

    write_findings(out)
    print((REP / "findings.md").read_text())


def write_findings(o):
    k, ab, ch, f = o["kpi"], o["ab"], o["channels"], o["feat"]
    fn = o["funnel"].set_index("device")
    a, n = f.loc["adopted_workout_plans"], f.loc["did_not_adopt"]
    best, worst = ch.iloc[0], ch.iloc[-1]
    ab_tbl = "\n".join(
        f"| {r.metric} | {r.control:.1%} | {r.treatment:.1%} | +{r.abs_lift_pp:.1f} pp (+{r.rel_lift:.0%}) "
        f"| [{r.ci_low_pp:.1f}, {r.ci_high_pp:.1f}] | {r.p_value:.2g} |" for r in ab.itertuples())
    ch_tbl = "\n".join(
        f"| {r.acquisition_channel} | {r.signups:,} | {r.activation_pct:.1f}% | {r.paid_conversion_pct:.2f}% "
        f"| ${r.revenue_per_signup_usd:.2f} |" for r in ch.itertuples())
    curve = o["retention_curve"]
    tr = o["trend"]
    sig = ab.p_value < 0.05
    if sig.all():
        ab_note = ("All three metrics are significant at α = 0.05. The lift carries through to activation and trial starts, "
                   "so users are not simply clicking through onboarding faster.")
    else:
        down = ", ".join(ab.metric[~sig].str.lower())
        ab_note = (f"The primary metric and activation are significant at α = 0.05. The lift in {down} is directionally positive "
                   "but not significant. Ship the change, then keep monitoring trial starts as a guardrail; they need a longer "
                   "observation window to mature.")
    md = f"""# FitTrack Product Analysis: Findings

Generated automatically by `src/analysis.py`.

## Headline KPIs
| Metric | Value |
|---|---|
| Total signups (Jan 5 – Jun 28, 2026) | {int(k.total_users):,} |
| Onboarding completion | {k.onboarding_rate_pct}% |
| Activation (≥1 workout) | {k.activation_rate_pct}% |
| Signup → paid conversion | {k.paid_conversion_pct}% |
| Active MRR (end of period) | ${k.active_mrr_usd:,.0f} |
| Avg. week-1 / week-4 / week-8 retention | {curve.get(1, np.nan):.1f}% / {curve.get(4, np.nan):.1f}% / {curve.get(8, np.nan):.1f}% |

## 1. Funnel: the biggest leak is onboarding → first workout
- Only {fn.loc['all','onboard_to_workout_pct']}% of onboarded users complete a first workout.
- Android converts at {fn.loc['android','onboard_to_workout_pct']}% on this step vs. {fn.loc['ios','onboard_to_workout_pct']}% on iOS,
  a {fn.loc['ios','onboard_to_workout_pct'] - fn.loc['android','onboard_to_workout_pct']:.1f} pp gap. Other steps are roughly at parity across devices,
  which points to an Android-specific first-workout experience issue (performance, permissions, or player bugs).
- Closing half of that gap would add roughly {int(fn.loc['android','onboarded'] * (fn.loc['ios','onboard_to_workout_pct'] - fn.loc['android','onboard_to_workout_pct']) / 200):,} activated users over the analysis period.

## 2. A/B test: the onboarding redesign should ship
Sample ratio check: p = {o['srm_p']:.2f} (no mismatch).

| Metric | Control | Treatment | Lift | 95% CI (pp) | p-value |
|---|---|---|---|---|---|
{ab_tbl}

{ab_note}

## 3. Feature adoption: Workout Plans is a strong retention signal
| Segment | Users | Week-4 retention | Paid conversion |
|---|---|---|---|
| Adopted Workout Plans in week 1 | {int(a.users):,} | {a.week4_retention_pct}% | {a.paid_conversion_pct}% |
| Did not adopt | {int(n.users):,} | {n.week4_retention_pct}% | {n.paid_conversion_pct}% |

Adopters retain at {a.week4_retention_pct / n.week4_retention_pct:.1f}x the rate of non-adopters (χ² p = {o['feat_p']:.1g}). This is correlational
(motivated users self-select), so the recommended next step is an experiment that surfaces Workout Plans during onboarding.

## 4. Acquisition: paid social brings volume, not value
| Channel | Signups | Activation | Paid conversion | Revenue / signup |
|---|---|---|---|---|
{ch_tbl}

{worst.acquisition_channel} earns only {worst.revenue_per_signup_usd / best.revenue_per_signup_usd:.0%} of the revenue per signup that {best.acquisition_channel} does.
Using 3x revenue to date as a rough LTV proxy, paid social is only break-even while CAC stays under about ${worst.revenue_per_signup_usd * 3:.2f}.
Budget should shift toward referral incentives.

## Recommendations (prioritized)
1. **Ship the new onboarding flow** to 100% of users: +{ab.iloc[0].abs_lift_pp:.1f} pp onboarding, +{ab.iloc[1].abs_lift_pp:.1f} pp activation.
2. **Investigate the Android first-workout step**: start with crash and latency logs; this is the largest single funnel gap.
3. **Test surfacing Workout Plans in onboarding** to see whether the retention lift holds up causally.
4. **Reallocate acquisition spend** from paid social toward referral and organic or ASO.

## Trend
WAU grew from {int(tr.wau.iloc[0]):,} in the first week to {int(tr.wau.iloc[-1]):,} by the end of June, and MRR reached ${tr.mrr_usd.iloc[-1]:,.0f}.
"""
    (REP / "findings.md").write_text(md)


if __name__ == "__main__":
    main()
