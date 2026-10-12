-- KPI 4: Condition mix — volume, severity, share of total losses.
SELECT
    condition,
    COUNT(*) AS n_claims,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS pct_of_claims,
    ROUND(AVG(claim_cost), 2) AS avg_severity,
    ROUND(SUM(claim_cost), 2) AS total_incurred,
    ROUND(SUM(claim_cost) * 100.0 / SUM(SUM(claim_cost)) OVER (), 2)
        AS pct_of_losses
FROM claims
GROUP BY 1
ORDER BY total_incurred DESC;
