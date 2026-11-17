-- Signup -> onboarding -> first workout -> trial -> paid, overall and by device
WITH steps AS (
  SELECT u.user_id, u.device,
         MAX(e.event_name = 'onboarding_complete')  AS s2_onboarded,
         MAX(e.event_name = 'workout_completed')    AS s3_first_workout,
         MAX(e.event_name = 'trial_started')        AS s4_trial,
         MAX(e.event_name = 'subscription_started') AS s5_paid
  FROM users u LEFT JOIN events e USING (user_id)
  GROUP BY u.user_id, u.device
),
by_device AS (
  SELECT device, COUNT(*) AS signups, SUM(s2_onboarded) AS onboarded,
         SUM(s3_first_workout) AS first_workout, SUM(s4_trial) AS trial, SUM(s5_paid) AS paid
  FROM steps GROUP BY device
  UNION ALL
  SELECT 'all', COUNT(*), SUM(s2_onboarded), SUM(s3_first_workout), SUM(s4_trial), SUM(s5_paid)
  FROM steps
)
SELECT *,
       ROUND(100.0 * onboarded     / signups, 1)       AS signup_to_onboard_pct,
       ROUND(100.0 * first_workout / onboarded, 1)     AS onboard_to_workout_pct,
       ROUND(100.0 * trial         / first_workout, 1) AS workout_to_trial_pct,
       ROUND(100.0 * paid          / trial, 1)         AS trial_to_paid_pct
FROM by_device
ORDER BY device = 'all' DESC, signups DESC;
