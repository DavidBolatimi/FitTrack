-- Acquisition channel quality: activation, paid conversion, revenue per signup
WITH u AS (
  SELECT u.user_id, u.acquisition_channel,
         MAX(e.event_name = 'workout_completed')    AS activated,
         MAX(e.event_name = 'subscription_started') AS paid
  FROM users u LEFT JOIN events e USING (user_id)
  GROUP BY 1, 2
),
rev AS (
  SELECT user_id,
         SUM(mrr_usd * ((julianday(COALESCE(end_ts, '2026-06-28')) - julianday(start_ts)) / 30.44)) AS revenue
  FROM subscriptions GROUP BY 1
)
SELECT acquisition_channel,
       COUNT(*)                                    AS signups,
       ROUND(100.0 * AVG(activated), 1)            AS activation_pct,
       ROUND(100.0 * AVG(paid), 2)                 AS paid_conversion_pct,
       ROUND(SUM(COALESCE(r.revenue, 0)), 0)       AS revenue_to_date_usd,
       ROUND(SUM(COALESCE(r.revenue, 0)) / COUNT(*), 2) AS revenue_per_signup_usd
FROM u LEFT JOIN rev r USING (user_id)
GROUP BY 1 ORDER BY revenue_per_signup_usd DESC;
