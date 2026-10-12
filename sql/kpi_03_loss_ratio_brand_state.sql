-- KPI 3: Loss ratio by brand x state (Tableau drill-down: brand -> state).
SELECT
    p.brand,
    p.state,
    p.territory,
    COUNT(DISTINCT p.policy_id) AS policies,
    ROUND(SUM(p.earned_premium), 2) AS earned_premium,
    ROUND(COALESCE(SUM(c.claim_cost), 0), 2) AS incurred_losses,
    ROUND(COALESCE(SUM(c.claim_cost), 0)
          / NULLIF(SUM(p.earned_premium), 0), 4) AS loss_ratio
FROM policies p
LEFT JOIN claims c ON c.policy_id = p.policy_id
GROUP BY 1, 2, 3
ORDER BY loss_ratio DESC;
