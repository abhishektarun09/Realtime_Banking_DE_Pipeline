{{ config(materialized='incremental', unique_key='transaction_id') }}

SELECT
    t.transaction_id,
    t.account_id,
    a.customer_id,
    t.amount,
    t.related_account_id,
    t.status,
    t.transaction_type,
    t.transaction_time,
    CURRENT_TIMESTAMP AS load_timestamp
FROM {{ ref('staging_transactions') }} t
LEFT JOIN {{ ref('staging_accounts') }} a
    ON t.account_id = a.account_id