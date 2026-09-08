SELECT
    event_date,
    platform,
    event_name,
    COUNT(*) AS event_count,
    COUNT(DISTINCT user_id) AS unique_users
FROM analytics.user_events
WHERE event_date BETWEEN {{ start_date }} AND {{ end_date }}
  AND platform = {{ platform | sql_literal }}
GROUP BY
    event_date,
    platform,
    event_name
ORDER BY
    event_date,
    event_count DESC
