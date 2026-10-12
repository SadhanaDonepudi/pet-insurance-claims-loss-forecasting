-- KPI 1: Monthly loss ratio by brand.
-- loss_ratio = SUM(claim_cost) / SUM(earned premium).
-- Earned premium comes from the policy_months mart table (each policy's
-- earned premium spread uniformly over its active in-window months).
WITH earned AS (
    SELECT brand, month, SUM(earned_premium) AS earned_premium
    FROM policy_months
    GROUP BY 1, 2
),
incurred AS (
    SELECT brand, substr(claim_date, 1, 7) AS month,
           SUM(claim_cost) AS incurred_losses,
           COUNT(*) AS n_claims
    FROM claims
    GROUP BY 1, 2
)
SELECT
    e.month,
    e.brand,
    ROUND(e.earned_premium, 2) AS earned_premium,
    ROUND(COALESCE(i.incurred_losses, 0), 2) AS incurred_losses,
    COALESCE(i.n_claims, 0) AS n_claims,
    ROUND(COALESCE(i.incurred_losses, 0) / NULLIF(e.earned_premium, 0), 4)
        AS loss_ratio
FROM earned e
LEFT JOIN incurred i ON i.brand = e.brand AND i.month = e.month
ORDER BY 1, 2;
