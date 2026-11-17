"""
Generate a realistic synthetic product dataset for "FitTrack", a fictional
freemium fitness app. Produces users, events, and subscriptions tables.

Embedded "ground truth" behaviors the analysis should uncover:
  * A/B test: new onboarding flow (treatment) lifts onboarding completion.
  * Users who adopt "Workout Plans" in week 1 retain significantly better.
  * Paid social users convert worse than organic / referral users.
  * Android users hit more friction at the first-workout step.
"""
import numpy as np
import pandas as pd
from pathlib import Path

SEED = 42
N_USERS = 25_000
START = pd.Timestamp("2026-01-05")
SIGNUP_WEEKS = 25
OBS_END = pd.Timestamp("2026-06-28")

rng = np.random.default_rng(SEED)
OUT = Path(__file__).resolve().parents[1] / "data"
OUT.mkdir(exist_ok=True)

channels = ["organic", "paid_social", "paid_search", "referral", "app_store"]
channel_p = [0.30, 0.25, 0.20, 0.10, 0.15]
channel_quality = {"organic": 1.00, "paid_social": 0.72, "paid_search": 0.90,
                   "referral": 1.20, "app_store": 0.95}
devices = ["ios", "android", "web"]
device_p = [0.48, 0.40, 0.12]
countries = ["US", "UK", "CA", "DE", "IN", "BR"]
country_p = [0.45, 0.12, 0.10, 0.10, 0.13, 0.10]

users = pd.DataFrame({
    "user_id": np.arange(1, N_USERS + 1),
    "signup_ts": START + pd.to_timedelta(rng.uniform(0, SIGNUP_WEEKS * 7, N_USERS), unit="D"),
    "acquisition_channel": rng.choice(channels, N_USERS, p=channel_p),
    "device": rng.choice(devices, N_USERS, p=device_p),
    "country": rng.choice(countries, N_USERS, p=country_p),
    "age_bucket": rng.choice(["18-24", "25-34", "35-44", "45+"], N_USERS, p=[.22, .38, .25, .15]),
})
users["signup_ts"] = users["signup_ts"].dt.floor("min")
# A/B test on onboarding ran for users signing up in weeks 5-12
in_test = (users.signup_ts >= START + pd.Timedelta(weeks=4)) & (users.signup_ts < START + pd.Timedelta(weeks=12))
users["experiment_group"] = np.where(in_test, rng.choice(["control", "treatment"], N_USERS), None)

events, subs = [], []

def add(uid, name, ts, **props):
    events.append((uid, name, ts, props.get("feature")))

for u in users.itertuples(index=False):
    q = channel_quality[u.acquisition_channel]
    t0 = u.signup_ts
    add(u.user_id, "signup", t0)

    # Onboarding completion
    p_onb = 0.62 * (0.9 + 0.1 * q)
    if u.experiment_group == "treatment":
        p_onb += 0.07
    if rng.random() > min(p_onb, 0.95):
        continue
    t = t0 + pd.Timedelta(minutes=float(rng.gamma(2, 4)))
    add(u.user_id, "onboarding_complete", t)

    # First workout
    p_fw = 0.70 * q * (0.80 if u.device == "android" else 1.0)
    if rng.random() > min(p_fw, 0.95):
        continue
    t = t + pd.Timedelta(hours=float(rng.gamma(1.5, 10)))
    add(u.user_id, "workout_completed", t)

    # Week-1 feature adoption
    adopts_plans = rng.random() < 0.35 * q
    if adopts_plans:
        add(u.user_id, "feature_used", t + pd.Timedelta(hours=float(rng.uniform(1, 120))), feature="workout_plans")
    if rng.random() < 0.45:
        add(u.user_id, "feature_used", t + pd.Timedelta(hours=float(rng.uniform(1, 150))), feature="nutrition_log")
    if rng.random() < 0.20:
        add(u.user_id, "feature_used", t + pd.Timedelta(hours=float(rng.uniform(1, 150))), feature="social_challenges")

    # Ongoing weekly engagement with decay (retention curve)
    base = 0.62 * q * (1.25 if adopts_plans else 0.9)
    base = min(base, 0.93)
    week, active = 1, True
    while active:
        wk_start = t0 + pd.Timedelta(weeks=week)
        if wk_start > OBS_END:
            break
        p_active = base * (0.93 ** (week - 1)) + 0.04
        if rng.random() < p_active:
            for _ in range(rng.poisson(2.2) + 1):
                ts = wk_start + pd.Timedelta(hours=float(rng.uniform(0, 167)))
                if ts <= OBS_END:
                    add(u.user_id, "workout_completed", ts)
        elif rng.random() < 0.55:
            active = False  # churned
        week += 1

    # Trial -> paid
    p_trial = 0.38 * q * (1.3 if adopts_plans else 1.0)
    if rng.random() < min(p_trial, 0.9):
        ts_trial = t + pd.Timedelta(days=float(rng.uniform(1, 10)))
        if ts_trial <= OBS_END:
            add(u.user_id, "trial_started", ts_trial)
            p_paid = 0.42 * q * (1.2 if adopts_plans else 1.0)
            if rng.random() < min(p_paid, 0.9):
                ts_paid = ts_trial + pd.Timedelta(days=7)
                if ts_paid <= OBS_END:
                    plan = rng.choice(["monthly", "annual"], p=[0.7, 0.3])
                    mrr = 12.99 if plan == "monthly" else round(99.99 / 12, 2)
                    add(u.user_id, "subscription_started", ts_paid)
                    months = rng.geometric(0.12 if plan == "monthly" else 0.04)
                    end = ts_paid + pd.DateOffset(months=int(months))
                    end = end if end <= OBS_END else pd.NaT
                    if pd.notna(end):
                        add(u.user_id, "subscription_cancelled", end)
                    subs.append((u.user_id, plan, ts_paid, end, mrr))

ev = pd.DataFrame(events, columns=["user_id", "event_name", "event_ts", "feature"])
ev = ev.sort_values(["event_ts"]).reset_index(drop=True)
ev.insert(0, "event_id", np.arange(1, len(ev) + 1))
ev["event_ts"] = ev["event_ts"].dt.floor("s")
sub = pd.DataFrame(subs, columns=["user_id", "plan", "start_ts", "end_ts", "mrr_usd"])
sub.insert(0, "subscription_id", np.arange(1, len(sub) + 1))

users.to_csv(OUT / "users.csv", index=False)
ev.to_csv(OUT / "events.csv.gz", index=False, compression="gzip")
sub.to_csv(OUT / "subscriptions.csv", index=False)
print(f"users={len(users):,} events={len(ev):,} subscriptions={len(sub):,}")
