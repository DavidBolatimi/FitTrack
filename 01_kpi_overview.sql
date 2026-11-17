-- Headline KPIs: users, activation, paid conversion, active MRR
WITH firsts AS (
  SELECT user_id,
         MAX(event_name = 'onboarding_complete')  AS onboarded,
         MAX(event_name = 'workout_completed')    AS activated,
         MAX(event_name = 'subscription_started') AS paid
  FROM events GROUP BY user_id
)
SELECT COUNT(*)                                   AS total_users,
       ROUND(100.0 * AVG(onboarded), 1)           AS onboarding_rate_pct,
       ROUND(100.0 * AVG(activated), 1)           AS activation_rate_pct,
       ROUND(100.0 * AVG(paid), 2)                AS paid_conversion_pct,
       (SELECT ROUND(SUM(mrr_usd), 2) FROM subscriptions WHERE end_ts IS NULL) AS active_mrr_usd
FROM firsts;
