"""Builds notebooks/fittrack_analysis.ipynb (run: python notebooks/build_notebook.py)."""
import nbformat as nbf
nb = nbf.v4.new_notebook()
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
nb.cells = [
    md("# FitTrack Product Analytics: Exploratory Notebook\n"
       "This is an interactive walkthrough of the analysis. The reusable logic lives in `../src` and `../sql`, and this notebook "
       "explores it step by step.\n\n**Business question:** Where are we losing users between signup and paid, and which "
       "levers (onboarding, features, channels) will grow subscription revenue?"),
    code("import sys, sqlite3\nsys.path.append('../src')\nimport pandas as pd\nfrom scipy import stats\n"
         "from build_database import build\nfrom analysis import two_prop_ztest, srm_check\n"
         "con = sqlite3.connect(build())\nsql = lambda f: pd.read_sql(open(f'../sql/{f}').read(), con)\n"
         "pd.set_option('display.width', 160)"),
    md("## 1. Data sanity checks"),
    code("for t in ['users', 'events', 'subscriptions']:\n"
         "    print(t, pd.read_sql(f'SELECT COUNT(*) n FROM {t}', con).n[0])\n"
         "pd.read_sql('SELECT event_name, COUNT(*) n FROM events GROUP BY 1 ORDER BY n DESC', con)"),
    code("# Every user should have exactly one signup event, and nobody should subscribe without a trial\n"
         "pd.read_sql('''SELECT\n  (SELECT COUNT(*) FROM users) - (SELECT COUNT(DISTINCT user_id) FROM events WHERE event_name='signup') AS missing_signups,\n"
         "  (SELECT COUNT(*) FROM subscriptions s WHERE NOT EXISTS (SELECT 1 FROM events e WHERE e.user_id=s.user_id AND e.event_name='trial_started')) AS subs_without_trial''', con)"),
    md("## 2. Headline KPIs"),
    code("sql('01_kpi_overview.sql')"),
    md("## 3. Funnel by device\nThe onboard → first workout step is the largest drop-off, and Android trails iOS by about 14 pp on it."),
    code("sql('02_funnel.sql')"),
    md("## 4. Onboarding A/B test\nThe test checks sample ratio mismatch first, then runs two-proportion z-tests on the primary and secondary metrics."),
    code("ab = sql('04_ab_test_onboarding.sql').set_index('experiment_group')\n"
         "print('SRM p-value:', round(srm_check(ab.loc['control','users'], ab.loc['treatment','users']), 3))\n"
         "rows = []\nfor m in ['onboarded', 'activated', 'trials']:\n"
         "    p1, p2, z, p, ci = two_prop_ztest(ab.loc['control', m], ab.loc['control','users'], ab.loc['treatment', m], ab.loc['treatment','users'])\n"
         "    rows.append(dict(metric=m, control=round(p1,4), treatment=round(p2,4), lift_pp=round((p2-p1)*100,2), ci_pp=(round(ci[0]*100,2), round(ci[1]*100,2)), p_value=p))\n"
         "pd.DataFrame(rows)"),
    code("# Power check: minimum detectable effect for onboarding completion at 80% power, alpha = 0.05\n"
         "import numpy as np\nn = ab.loc['control','users']; p = ab.loc['control','onboarded'] / n\n"
         "mde = (stats.norm.ppf(0.975) + stats.norm.ppf(0.8)) * np.sqrt(2 * p * (1 - p) / n)\n"
         "print(f'MDE ≈ {mde*100:.2f} pp with {n:,} users per arm')"),
    md("## 5. Feature adoption vs. retention"),
    code("sql('05_feature_adoption_retention.sql')"),
    md("## 6. Channel quality"),
    code("sql('06_channel_performance.sql')"),
    md("## 7. Cohort retention"),
    code("ret = sql('03_weekly_retention_cohorts.sql')\nret.pivot(index='cohort_week', columns='week_n', values='retention_pct').round(0)"),
    md("## Figures\nRun `python src/analysis.py` to regenerate every chart in `reports/figures/` and the written summary in `reports/findings.md`."),
]
nbf.write(nb, "notebooks/fittrack_analysis.ipynb")
print("written")
