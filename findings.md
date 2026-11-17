# FitTrack Product Analysis: Findings

Generated automatically by `src/analysis.py`.

## Headline KPIs
| Metric | Value |
|---|---|
| Total signups (Jan 5 – Jun 28, 2026) | 25,000 |
| Onboarding completion | 62.3% |
| Activation (≥1 workout) | 37.4% |
| Signup → paid conversion | 5.91% |
| Active MRR (end of period) | $13,548 |
| Avg. week-1 / week-4 / week-8 retention | 23.9% / 10.0% / 2.6% |

## 1. Funnel: the biggest leak is onboarding → first workout
- Only 60.0% of onboarded users complete a first workout.
- Android converts at 51.5% on this step vs. 65.7% on iOS,
  a 14.2 pp gap. Other steps are roughly at parity across devices,
  which points to an Android-specific first-workout experience issue (performance, permissions, or player bugs).
- Closing half of that gap would add roughly 438 activated users over the analysis period.

## 2. A/B test: the onboarding redesign should ship
Sample ratio check: p = 0.98 (no mismatch).

| Metric | Control | Treatment | Lift | 95% CI (pp) | p-value |
|---|---|---|---|---|---|
| Onboarding completion | 60.8% | 68.8% | +8.0 pp (+13%) | [5.9, 10.1] | 1.2e-13 |
| Activation (first workout) | 37.4% | 41.8% | +4.3 pp (+12%) | [2.2, 6.5] | 8.7e-05 |
| Trial start | 15.1% | 16.2% | +1.1 pp (+7%) | [-0.5, 2.7] | 0.18 |

The primary metric and activation are significant at α = 0.05. The lift in trial start is directionally positive but not significant. Ship the change, then keep monitoring trial starts as a guardrail; they need a longer observation window to mature.

## 3. Feature adoption: Workout Plans is a strong retention signal
| Segment | Users | Week-4 retention | Paid conversion |
|---|---|---|---|
| Adopted Workout Plans in week 1 | 2,482 | 40.2% | 22.6% |
| Did not adopt | 4,971 | 19.7% | 14.5% |

Adopters retain at 2.0x the rate of non-adopters (χ² p = 2e-79). This is correlational
(motivated users self-select), so the recommended next step is an experiment that surfaces Workout Plans during onboarding.

## 4. Acquisition: paid social brings volume, not value
| Channel | Signups | Activation | Paid conversion | Revenue / signup |
|---|---|---|---|---|
| referral | 2,527 | 51.2% | 12.62% | $3.48 |
| organic | 7,448 | 41.2% | 7.14% | $1.95 |
| app_store | 3,742 | 38.0% | 6.12% | $1.63 |
| paid_search | 5,055 | 36.0% | 4.99% | $1.30 |
| paid_social | 6,228 | 28.0% | 2.33% | $0.65 |

paid_social earns only 19% of the revenue per signup that referral does.
Using 3x revenue to date as a rough LTV proxy, paid social is only break-even while CAC stays under about $1.95.
Budget should shift toward referral incentives.

## Recommendations (prioritized)
1. **Ship the new onboarding flow** to 100% of users: +8.0 pp onboarding, +4.3 pp activation.
2. **Investigate the Android first-workout step**: start with crash and latency logs; this is the largest single funnel gap.
3. **Test surfacing Workout Plans in onboarding** to see whether the retention lift holds up causally.
4. **Reallocate acquisition spend** from paid social toward referral and organic or ASO.

## Trend
WAU grew from 328 in the first week to 1,316 by the end of June, and MRR reached $13,548.
