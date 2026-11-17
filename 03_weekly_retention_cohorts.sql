-- Weekly signup cohorts x weeks since signup (activity = completed a workout)
WITH activity AS (
  SELECT DISTINCT e.user_id,
         CAST((julianday(e.event_ts) - julianday(u.signup_ts)) / 7 AS INT) AS week_n
  FROM events e JOIN users u USING (user_id)
  WHERE e.event_name = 'workout_completed'
),
cohorts AS (
  SELECT user_id,
         date(signup_ts, '-6 days', 'weekday 1') AS cohort_week
  FROM users
),
sizes AS (SELECT cohort_week, COUNT(*) AS cohort_size FROM cohorts GROUP BY 1)
SELECT c.cohort_week, s.cohort_size, a.week_n,
       COUNT(DISTINCT a.user_id) AS active_users,
       ROUND(100.0 * COUNT(DISTINCT a.user_id) / s.cohort_size, 1) AS retention_pct
FROM cohorts c
JOIN activity a USING (user_id)
JOIN sizes s USING (cohort_week)
WHERE a.week_n BETWEEN 0 AND 12
  -- only count weeks the cohort has fully observed
  AND julianday(c.cohort_week) + 7 * (a.week_n + 2) <= julianday('2026-06-28')
GROUP BY 1, 2, 3
ORDER BY 1, 3;
