
use olist_db;

-- Monthly Revenue Trend

SELECT 
    FORMAT(CAST(o.order_purchase_timestamp AS DATETIME), 'yyyy-MM') AS order_month,
    SUM(CAST(op.payment_value AS FLOAT)) AS total_revenue,
    COUNT(DISTINCT o.order_id) AS total_orders
FROM dbo.orders o
JOIN dbo.order_payments op 
    ON o.order_id = op.order_id
WHERE o.order_status = 'delivered'
GROUP BY FORMAT(CAST(o.order_purchase_timestamp AS DATETIME), 'yyyy-MM')
ORDER BY order_month;


-- Revenue Growth Rate

WITH monthly_revenue AS (
    SELECT 
        FORMAT(CAST(o.order_purchase_timestamp AS DATETIME), 'yyyy-MM') AS order_month,
        SUM(CAST(op.payment_value AS FLOAT)) AS revenue
    FROM dbo.orders o
    JOIN dbo.order_payments op 
        ON o.order_id = op.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY FORMAT(CAST(o.order_purchase_timestamp AS DATETIME), 'yyyy-MM')
)

SELECT 
    order_month,
    revenue,
    LAG(revenue) OVER (ORDER BY order_month) AS prev_month_revenue,
    CASE 
        WHEN LAG(revenue) OVER (ORDER BY order_month) IS NULL THEN NULL
        ELSE 
            (revenue - LAG(revenue) OVER (ORDER BY order_month)) * 100.0 
            / LAG(revenue) OVER (ORDER BY order_month)
    END AS growth_percentage
FROM monthly_revenue
ORDER BY order_month;



-- Top Categories by Revenue

SELECT TOP 10
    p.product_category_name,
    SUM(CAST(oi.price AS FLOAT)) AS total_revenue,
    COUNT(DISTINCT oi.order_id) AS total_orders
FROM dbo.order_items oi
JOIN dbo.products p 
    ON oi.product_id = p.product_id
GROUP BY p.product_category_name
ORDER BY total_revenue DESC;


-- Revenue by State

SELECT 
    c.customer_state,
    SUM(CAST(op.payment_value AS FLOAT)) AS total_revenue,
    COUNT(DISTINCT o.order_id) AS total_orders
FROM dbo.orders o
JOIN dbo.customers c 
    ON o.customer_id = c.customer_id
JOIN dbo.order_payments op 
    ON o.order_id = op.order_id
WHERE o.order_status = 'delivered'
GROUP BY c.customer_state
ORDER BY total_revenue DESC;



-- Average Order Value

SELECT 
    SUM(CAST(op.payment_value AS FLOAT)) / COUNT(DISTINCT o.order_id) AS avg_order_value
FROM dbo.orders o
JOIN dbo.order_payments op 
    ON o.order_id = op.order_id
WHERE o.order_status = 'delivered';


-- Top Customers

SELECT TOP 10
    c.customer_unique_id,
    SUM(CAST(op.payment_value AS FLOAT)) AS total_spent,
    COUNT(DISTINCT o.order_id) AS total_orders
FROM dbo.orders o
JOIN dbo.customers c 
    ON o.customer_id = c.customer_id
JOIN dbo.order_payments op 
    ON o.order_id = op.order_id
WHERE o.order_status = 'delivered'
GROUP BY c.customer_unique_id
ORDER BY total_spent DESC;



-- fixes

ALTER TABLE dbo.orders
ALTER COLUMN order_purchase_timestamp DATETIME;

ALTER TABLE dbo.order_payments
ALTER COLUMN payment_value FLOAT;

ALTER TABLE dbo.order_items
ALTER COLUMN price FLOAT;