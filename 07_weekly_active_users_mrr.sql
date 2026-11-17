-- Weekly active users (WAU) and end-of-week MRR trend
WITH weeks AS (
  SELECT DISTINCT date(event_ts, '-6 days', 'weekday 1') AS week_start FROM events
),
wau AS (
  SELECT date(event_ts, '-6 days', 'weekday 1') AS week_start, COUNT(DISTINCT user_id) AS wau
  FROM events WHERE event_name = 'workout_completed' GROUP BY 1
)
SELECT w.week_start, COALESCE(wau.wau, 0) AS wau,
       ROUND((SELECT SUM(s.mrr_usd) FROM subscriptions s
              WHERE s.start_ts < date(w.week_start, '+7 days')
                AND (s.end_ts IS NULL OR s.end_ts >= date(w.week_start, '+7 days'))), 2) AS mrr_usd
FROM weeks w LEFT JOIN wau USING (week_start)
WHERE w.week_start <= '2026-06-22'
ORDER BY 1;
