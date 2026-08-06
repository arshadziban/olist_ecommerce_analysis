CREATE DATABASE olist_db;
USE olist_db;


SELECT 'customers'      AS tbl, COUNT(*) AS rows FROM customers      UNION ALL
SELECT 'orders'         AS tbl, COUNT(*) AS rows FROM orders          UNION ALL
SELECT 'order_items'    AS tbl, COUNT(*) AS rows FROM order_items     UNION ALL
SELECT 'order_payments' AS tbl, COUNT(*) AS rows FROM order_payments  UNION ALL
SELECT 'products'       AS tbl, COUNT(*) AS rows FROM products;

