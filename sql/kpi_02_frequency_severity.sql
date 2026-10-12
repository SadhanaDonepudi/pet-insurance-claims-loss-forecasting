-- KPI 2: Claim frequency and average severity by breed.
-- frequency_per_1k_ey = claims / exposure_years * 1000
-- severity           = AVG(claim_cost)
SELECT
    p.breed,
    p.species,
    COUNT(DISTINCT p.policy_id) AS policies,
    ROUND(SUM(p.in_window_exposure_years), 1) AS exposure_years,
    COUNT(c.claim_id) AS n_claims,
    ROUND(COUNT(c.claim_id)
          / NULLIF(SUM(p.in_window_exposure_years), 0) * 1000, 2)
        AS frequency_per_1k_ey,
    ROUND(AVG(c.claim_cost), 2) AS avg_severity,
    ROUND(COALESCE(SUM(c.claim_cost), 0), 2) AS total_incurred
FROM policies p
LEFT JOIN claims c ON c.policy_id = p.policy_id
GROUP BY 1, 2
ORDER BY frequency_per_1k_ey DESC;
