-- Read-only checks after opt-in fixture setup. These execute warehouse queries.
SELECT COUNT(*) AS sale_lines, SUM(s.units) AS units, SUM(s.net_revenue_usd) AS revenue_usd
FROM northstar_demo.retail.sales AS s;
-- Expected fixture-only result: 6, 15, 1350.00.

SELECT i.product_id, i.warehouse, i.on_hand_units, i.reorder_point_units
FROM northstar_demo.retail.inventory AS i
WHERE i.snapshot_date = DATE'2026-10-03' AND i.on_hand_units < i.reorder_point_units
ORDER BY i.product_id, i.warehouse;
-- Expected: SKU-100/Boston, SKU-200/Reno, SKU-300/Reno.
