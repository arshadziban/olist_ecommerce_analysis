use olist_db;

-- full retention table per cohort per month

with customer_cohorts as (
    select
        c.customer_unique_id,
        datefromparts(
            year(min(cast(o.order_purchase_timestamp as datetime))),
            month(min(cast(o.order_purchase_timestamp as datetime))),
            1
        ) as cohort_month
    from orders o
    join customers c
        on o.customer_id = c.customer_id
    where o.order_status = 'delivered'
      and o.order_purchase_timestamp is not null
    group by
        c.customer_unique_id
),

customer_activity as (
    select
        c.customer_unique_id,
        datefromparts(
            year(cast(o.order_purchase_timestamp as datetime)),
            month(cast(o.order_purchase_timestamp as datetime)),
            1
        ) as activity_month
    from orders o
    join customers c
        on o.customer_id = c.customer_id
    where o.order_status = 'delivered'
      and o.order_purchase_timestamp is not null
    group by
        c.customer_unique_id,
        year(cast(o.order_purchase_timestamp as datetime)),
        month(cast(o.order_purchase_timestamp as datetime))
),

cohort_data as (
    select
        cc.cohort_month,
        ca.activity_month,
        count(distinct ca.customer_unique_id)               as active_customers,
        datediff(month, cc.cohort_month, ca.activity_month) as cohort_index
    from customer_cohorts cc
    join customer_activity ca
        on cc.customer_unique_id = ca.customer_unique_id
    where ca.activity_month >= cc.cohort_month
    group by
        cc.cohort_month,
        ca.activity_month,
        datediff(month, cc.cohort_month, ca.activity_month)
),

cohort_sizes as (
    select
        cohort_month,
        active_customers as cohort_size
    from cohort_data
    where cohort_index = 0
)

select
    cd.cohort_month,
    cd.cohort_index,
    cs.cohort_size,
    cd.active_customers,
    round(100.0 * cd.active_customers / cs.cohort_size, 2) as retention_rate_pct
from cohort_data cd
join cohort_sizes cs
    on cd.cohort_month = cs.cohort_month
order by
    cd.cohort_month,
    cd.cohort_index;
go



-- average retention by cohort index (summary view)

with customer_cohorts as (
    select
        c.customer_unique_id,
        datefromparts(
            year(min(cast(o.order_purchase_timestamp as datetime))),
            month(min(cast(o.order_purchase_timestamp as datetime))),
            1
        ) as cohort_month
    from orders o
    join customers c
        on o.customer_id = c.customer_id
    where o.order_status = 'delivered'
      and o.order_purchase_timestamp is not null
    group by
        c.customer_unique_id
),

customer_activity as (
    select
        c.customer_unique_id,
        datefromparts(
            year(cast(o.order_purchase_timestamp as datetime)),
            month(cast(o.order_purchase_timestamp as datetime)),
            1
        ) as activity_month
    from orders o
    join customers c
        on o.customer_id = c.customer_id
    where o.order_status = 'delivered'
      and o.order_purchase_timestamp is not null
    group by
        c.customer_unique_id,
        year(cast(o.order_purchase_timestamp as datetime)),
        month(cast(o.order_purchase_timestamp as datetime))
),

cohort_data as (
    select
        cc.cohort_month,
        datediff(month, cc.cohort_month, ca.activity_month) as cohort_index,
        count(distinct ca.customer_unique_id)               as active_customers
    from customer_cohorts cc
    join customer_activity ca
        on cc.customer_unique_id = ca.customer_unique_id
    where ca.activity_month >= cc.cohort_month
    group by
        cc.cohort_month,
        datediff(month, cc.cohort_month, ca.activity_month)
),

cohort_sizes as (
    select
        cohort_month,
        active_customers as cohort_size
    from cohort_data
    where cohort_index = 0
)

select
    cd.cohort_index                                              as months_since_acquisition,
    count(distinct cd.cohort_month)                             as num_cohorts,
    sum(cd.active_customers)                                    as total_active,
    round(avg(100.0 * cd.active_customers / cs.cohort_size), 2) as avg_retention_pct
from cohort_data cd
join cohort_sizes cs
    on cd.cohort_month = cs.cohort_month
group by
    cd.cohort_index
order by
    cd.cohort_index;
go