# FitTrack Product Analytics: Funnel, Retention, A/B Testing & Growth Levers

> An end-to-end product analytics case study for a freemium fitness app. I find where users drop off between signup and paid, test whether a redesigned onboarding flow should ship, and size the growth levers in retention and acquisition.

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![SQL](https://img.shields.io/badge/SQL-SQLite-lightgrey) ![Stats](https://img.shields.io/badge/Stats-A%2FB%20testing-green) ![License](https://img.shields.io/badge/license-MIT-black)

## Business Context
**FitTrack** is a fictional freemium fitness app: users sign up, complete onboarding, log workouts, start a 7-day free trial, and convert to a monthly ($12.99) or annual ($99.99) plan. Leadership asked four questions:

1. **Where is the funnel leaking**, and is the leak the same across platforms?
2. **Should we ship the redesigned onboarding flow** that was A/B tested on 7,900+ users?
3. **Which early behaviors predict retention** and conversion?
4. **Which acquisition channels bring valuable users**, and not just volume?

**Dataset:** 25,000 users, 124K events, and 1,477 subscriptions (Jan–Jun 2026). The data is synthetic and generated reproducibly with realistic behavioral patterns. See the [data dictionary](data/DATA_DICTIONARY.md).

## Key Findings

| # | Finding | Impact | Recommendation |
|---|---|---|---|
| 1 | Onboard → first workout is the largest drop-off (60% conversion). **Android trails iOS by 14 pp** on this step only. | About 440 activated users lost to the Android gap | Investigate Android first-workout performance and crashes |
| 2 | New onboarding lifted completion **+8.0 pp (60.8% → 68.8%, p < 0.001)** and activation **+4.3 pp (p < 0.001)**. There was no sample ratio mismatch. | +12% activation | **Ship to 100%**, and track trial starts as a guardrail metric |
| 3 | Users who adopt **Workout Plans in week 1 retain at 2x the rate** (40% vs. 20% week-4 retention) and convert 1.6x more often. | Strongest leading indicator | Run an experiment that surfaces Workout Plans in onboarding |
| 4 | **Paid social brings 25% of signups but only $0.65 revenue per signup**, versus $3.48 for referral (5.4x). | Inefficient spend | Cap paid social CAC and invest in referral incentives |

### Funnel
![Funnel](reports/figures/01_funnel.png)
![Funnel by device](reports/figures/02_funnel_by_device.png)

### A/B Test: Onboarding Redesign
| Metric | Control | Treatment | Lift | 95% CI | p-value |
|---|---|---|---|---|---|
| Onboarding completion (primary) | 60.8% | 68.8% | **+8.0 pp** | [5.9, 10.1] | 1e-13 |
| Activation (first workout) | 37.4% | 41.8% | **+4.3 pp** | [2.2, 6.5] | 9e-05 |
| Trial start | 15.1% | 16.2% | +1.1 pp | [-0.5, 2.7] | 0.18 |

The method checks sample ratio mismatch with a chi-square test, compares proportions with two-proportion z-tests, and estimates the minimum detectable effect (about 3.1 pp at 80% power). Trial start is directionally positive but underpowered, so it should keep being monitored after launch.

![A/B test](reports/figures/04_ab_test.png)

### Retention
![Retention heatmap](reports/figures/03_retention_heatmap.png)
![Feature adoption](reports/figures/05_feature_adoption.png)

> **Caveat:** Workout Plans adoption is correlational, since motivated users self-select into it. I recommend an experiment before claiming a causal effect.

### Acquisition Channels
![Channel quality](reports/figures/06_channel_quality.png)

### Growth Trend
![WAU and MRR](reports/figures/07_wau_mrr.png)

The full write-up is in [`reports/findings.md`](reports/findings.md).

## Repository Structure
```
├── data/
│   ├── users.csv              # 25K users with channel, device, and experiment group
│   ├── events.csv.gz          # 124K product events
│   ├── subscriptions.csv      # paid subscriptions and MRR
│   └── DATA_DICTIONARY.md
├── sql/                       # analysis queries (SQLite dialect, CTEs, window logic)
│   ├── 01_kpi_overview.sql
│   ├── 02_funnel.sql
│   ├── 03_weekly_retention_cohorts.sql
│   ├── 04_ab_test_onboarding.sql
│   ├── 05_feature_adoption_retention.sql
│   ├── 06_channel_performance.sql
│   └── 07_weekly_active_users_mrr.sql
├── src/
│   ├── generate_data.py       # reproducible synthetic data generator (seed = 42)
│   ├── build_database.py      # loads CSVs into SQLite
│   └── analysis.py            # runs SQL, stats tests, charts, and the findings report
├── notebooks/
│   └── fittrack_analysis.ipynb  # exploratory walkthrough with sanity and power checks
└── reports/
    ├── findings.md
    └── figures/
```

## How to Run
```bash
git clone https://github.com/<your-username>/fittrack-product-analytics.git
cd fittrack-product-analytics
pip install -r requirements.txt
python src/generate_data.py      # optional: regenerate the data
cd src && python analysis.py     # rebuilds the DB, figures, and findings.md
```

## Skills Demonstrated
- **SQL:** CTEs, conditional aggregation, cohort construction, date arithmetic, and correlated subqueries
- **Product metrics:** activation, funnel conversion, cohort retention, WAU, MRR, and revenue per signup
- **Experimentation:** SRM checks, two-proportion z-tests, confidence intervals, power/MDE, and guardrail metrics
- **Python:** pandas, SciPy, matplotlib, and a reproducible pipeline
- **Communication:** recommendations tied to sized business impact, with explicit caveats

## Next Steps
- Build a Tableau or Looker Studio dashboard on top of the SQL layer
- Model churn with logistic regression or survival analysis
- Use CUPED variance reduction for future experiments
