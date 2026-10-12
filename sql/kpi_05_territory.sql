-- KPI 5: Territory scorecard — loss ratio, frequency, severity.
SELECT
    p.territory,
    p.region,
    p.density,
    COUNT(DISTINCT p.policy_id) AS policies,
    ROUND(SUM(p.in_window_exposure_years), 1) AS exposure_years,
    COUNT(c.claim_id) AS n_claims,
    ROUND(COUNT(c.claim_id)
          / NULLIF(SUM(p.in_window_exposure_years), 0) * 1000, 2)
        AS frequency_per_1k_ey,
    ROUND(AVG(c.claim_cost), 2) AS avg_severity,
    ROUND(SUM(p.earned_premium), 2) AS earned_premium,
    ROUND(COALESCE(SUM(c.claim_cost), 0), 2) AS incurred_losses,
    ROUND(COALESCE(SUM(c.claim_cost), 0)
          / NULLIF(SUM(p.earned_premium), 0), 4) AS loss_ratio
FROM policies p
LEFT JOIN claims c ON c.policy_id = p.policy_id
GROUP BY 1, 2, 3
ORDER BY loss_ratio DESC;
