
use olist_db;
go
 
-- full rfm scores per customer

with reference_date as (
    select
        dateadd(day, 1, max(cast(order_purchase_timestamp as datetime))) as ref_date
    from orders
    where order_purchase_timestamp is not null
),

rfm_base as (
    select
        c.customer_unique_id,
        datediff(
            day,
            max(cast(o.order_purchase_timestamp as datetime)),
            (select ref_date from reference_date)
        )                                          as recency_days,
        count(distinct o.order_id)                 as frequency,
        sum(cast(p.payment_value as decimal(10,2))) as monetary
    from orders o
    join customers c
        on o.customer_id = c.customer_id
    join order_payments p
        on o.order_id = p.order_id
    where o.order_status = 'delivered'
      and o.order_purchase_timestamp is not null
    group by
        c.customer_unique_id
),

rfm_scores as (
    select
        customer_unique_id,
        recency_days,
        frequency,
        round(monetary, 2)                                 as monetary,
        ntile(5) over (order by recency_days desc)         as r_score,
        ntile(5) over (order by frequency asc)             as f_score,
        ntile(5) over (order by monetary asc)              as m_score
    from rfm_base
),

rfm_segments as (
    select
        customer_unique_id,
        recency_days,
        frequency,
        monetary,
        r_score,
        f_score,
        m_score,
        concat(r_score, f_score, m_score) as rfm_cell,
        case
            when r_score >= 4 and f_score >= 4  then 'Champions'
            when r_score >= 3 and f_score >= 3  then 'Loyal Customers'
            when r_score >= 4 and f_score < 3   then 'Recent Customers'
            when r_score >= 3 and f_score < 3   then 'Potential Loyalists'
            when r_score < 3  and f_score >= 3  then 'At Risk'
            when r_score < 2  and f_score >= 3  then 'Cannot Lose Them'
            when r_score < 2  and f_score < 2   then 'Lost'
            else                                     'Needs Attention'
        end as segment
    from rfm_scores
)

select
    customer_unique_id,
    recency_days,
    frequency,
    monetary,
    r_score,
    f_score,
    m_score,
    rfm_cell,
    segment
from rfm_segments
order by
    monetary desc;
go


--  segment summary
-- how many customers per segment + avg rfm values

with reference_date as (
    select
        dateadd(day, 1, max(cast(order_purchase_timestamp as datetime))) as ref_date
    from orders
    where order_purchase_timestamp is not null
),

rfm_base as (
    select
        c.customer_unique_id,
        datediff(
            day,
            max(cast(o.order_purchase_timestamp as datetime)),
            (select ref_date from reference_date)
        )                                          as recency_days,
        count(distinct o.order_id)                 as frequency,
        sum(cast(p.payment_value as decimal(10,2))) as monetary
    from orders o
    join customers c
        on o.customer_id = c.customer_id
    join order_payments p
        on o.order_id = p.order_id
    where o.order_status = 'delivered'
      and o.order_purchase_timestamp is not null
    group by
        c.customer_unique_id
),

rfm_scores as (
    select
        customer_unique_id,
        recency_days,
        frequency,
        monetary,
        ntile(5) over (order by recency_days desc) as r_score,
        ntile(5) over (order by frequency asc)     as f_score,
        ntile(5) over (order by monetary asc)      as m_score
    from rfm_base
),

rfm_segments as (
    select
        customer_unique_id,
        recency_days,
        frequency,
        monetary,
        r_score,
        f_score,
        m_score,
        case
            when r_score >= 4 and f_score >= 4  then 'Champions'
            when r_score >= 3 and f_score >= 3  then 'Loyal Customers'
            when r_score >= 4 and f_score < 3   then 'Recent Customers'
            when r_score >= 3 and f_score < 3   then 'Potential Loyalists'
            when r_score < 3  and f_score >= 3  then 'At Risk'
            when r_score < 2  and f_score >= 3  then 'Cannot Lose Them'
            when r_score < 2  and f_score < 2   then 'Lost'
            else                                     'Needs Attention'
        end as segment
    from rfm_scores
)

select
    segment,
    count(*)                          as customer_count,
    round(avg(recency_days), 1)       as avg_recency_days,
    round(avg(frequency), 2)          as avg_frequency,
    round(avg(monetary), 2)           as avg_monetary,
    round(sum(monetary), 2)           as total_revenue,
    round(
        100.0 * count(*) /
        sum(count(*)) over (), 2
    )                                 as pct_of_customers
from rfm_segments
group by
    segment
order by
    total_revenue desc;
go