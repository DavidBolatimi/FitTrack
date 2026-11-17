-- Onboarding redesign experiment: primary metric = onboarding completion,
-- secondary = first workout and trial start within the test population
WITH u AS (
  SELECT u.user_id, u.experiment_group,
         MAX(e.event_name = 'onboarding_complete') AS onboarded,
         MAX(e.event_name = 'workout_completed')   AS activated,
         MAX(e.event_name = 'trial_started')       AS trial
  FROM users u LEFT JOIN events e USING (user_id)
  WHERE u.experiment_group IS NOT NULL
  GROUP BY 1, 2
)
SELECT experiment_group,
       COUNT(*)       AS users,
       SUM(onboarded) AS onboarded,
       SUM(activated) AS activated,
       SUM(trial)     AS trials,
       ROUND(100.0 * AVG(onboarded), 2) AS onboarding_rate_pct,
       ROUND(100.0 * AVG(activated), 2) AS activation_rate_pct,
       ROUND(100.0 * AVG(trial), 2)     AS trial_rate_pct
FROM u GROUP BY 1 ORDER BY 1;
