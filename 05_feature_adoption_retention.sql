-- Do users who adopt Workout Plans in their first 7 days retain and convert better?
-- Restricted to activated users with >= 5 weeks of observation.
WITH base AS (
  SELECT u.user_id, u.signup_ts
  FROM users u
  WHERE EXISTS (SELECT 1 FROM events e WHERE e.user_id = u.user_id AND e.event_name = 'workout_completed')
    AND julianday('2026-06-28') - julianday(u.signup_ts) >= 35
),
flags AS (
  SELECT b.user_id,
    MAX(e.feature = 'workout_plans' AND julianday(e.event_ts) - julianday(b.signup_ts) < 7) AS adopted_plans_w1,
    MAX(e.event_name = 'workout_completed'
        AND julianday(e.event_ts) - julianday(b.signup_ts) BETWEEN 28 AND 35)              AS retained_w4,
    MAX(e.event_name = 'subscription_started')                                              AS paid
  FROM base b JOIN events e USING (user_id)
  GROUP BY b.user_id
)
SELECT CASE adopted_plans_w1 WHEN 1 THEN 'adopted_workout_plans' ELSE 'did_not_adopt' END AS segment,
       COUNT(*) AS users,
       ROUND(100.0 * AVG(retained_w4), 1) AS week4_retention_pct,
       ROUND(100.0 * AVG(paid), 1)        AS paid_conversion_pct
FROM flags GROUP BY 1;
