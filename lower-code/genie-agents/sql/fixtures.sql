-- OPT-IN PROVISIONING ONLY. Review names before executing in a SQL warehouse.
-- Creates synthetic demonstration data, never production data. No destructive replacement.
CREATE SCHEMA IF NOT EXISTS northstar_demo.retail;

CREATE TABLE IF NOT EXISTS northstar_demo.retail.sales (
  sale_id STRING COMMENT 'Unique sale line identifier.',
  sale_date DATE COMMENT 'Calendar sale date. Fixture covers October 1 to 3, 2026.',
  product_id STRING COMMENT 'Synthetic SKU identifier.',
  product_name STRING COMMENT 'Product display name.',
  category STRING COMMENT 'Product category.',
  region STRING COMMENT 'Sales region.',
  units INT COMMENT 'Units sold on this sale line.',
  net_revenue_usd DECIMAL(12,2) COMMENT 'Final net revenue in USD; already net of discounts. No returns or tax in this fixture.'
) USING DELTA COMMENT 'Northstar synthetic retail sales; one row per sale line.';

-- MERGE makes rerunning this small fixture idempotent on sale_id.
MERGE INTO northstar_demo.retail.sales AS target
USING (SELECT * FROM VALUES
  ('S001', DATE'2026-10-01', 'SKU-100', 'Trail Runner', 'Footwear', 'East', 3, 270.00),
  ('S002', DATE'2026-10-01', 'SKU-200', 'City Pack', 'Bags', 'West', 2, 120.00),
  ('S003', DATE'2026-10-02', 'SKU-100', 'Trail Runner', 'Footwear', 'West', 4, 360.00),
  ('S004', DATE'2026-10-02', 'SKU-300', 'Rain Shell', 'Apparel', 'East', 1, 140.00),
  ('S005', DATE'2026-10-03', 'SKU-200', 'City Pack', 'Bags', 'East', 3, 180.00),
  ('S006', DATE'2026-10-03', 'SKU-300', 'Rain Shell', 'Apparel', 'West', 2, 280.00)
  AS fixture(sale_id, sale_date, product_id, product_name, category, region, units, net_revenue_usd)) AS source
ON target.sale_id = source.sale_id
WHEN NOT MATCHED THEN INSERT *;

CREATE TABLE IF NOT EXISTS northstar_demo.retail.inventory (
  snapshot_date DATE COMMENT 'Daily inventory snapshot date; never sum across snapshot dates.',
  product_id STRING COMMENT 'Synthetic SKU identifier matching the sales table.',
  product_name STRING COMMENT 'Product display name.',
  category STRING COMMENT 'Product category.',
  warehouse STRING COMMENT 'Warehouse location.',
  on_hand_units INT COMMENT 'Units physically on hand at this warehouse on snapshot_date.',
  reorder_point_units INT COMMENT 'Demo warehouse-specific threshold; flag low stock when on_hand_units < reorder_point_units.'
) USING DELTA COMMENT 'Northstar synthetic inventory; one row per date, SKU, warehouse.';

MERGE INTO northstar_demo.retail.inventory AS target
USING (SELECT * FROM VALUES
  (DATE'2026-10-03', 'SKU-100', 'Trail Runner', 'Footwear', 'Boston', 4, 10),
  (DATE'2026-10-03', 'SKU-100', 'Trail Runner', 'Footwear', 'Reno', 18, 10),
  (DATE'2026-10-03', 'SKU-200', 'City Pack', 'Bags', 'Boston', 20, 8),
  (DATE'2026-10-03', 'SKU-200', 'City Pack', 'Bags', 'Reno', 5, 8),
  (DATE'2026-10-03', 'SKU-300', 'Rain Shell', 'Apparel', 'Boston', 12, 6),
  (DATE'2026-10-03', 'SKU-300', 'Rain Shell', 'Apparel', 'Reno', 2, 6)
  AS fixture(snapshot_date, product_id, product_name, category, warehouse, on_hand_units, reorder_point_units)) AS source
ON target.snapshot_date = source.snapshot_date AND target.product_id = source.product_id AND target.warehouse = source.warehouse
WHEN NOT MATCHED THEN INSERT *;
