{% snapshot snapshot_accounts %}
{{
    config(
      target_schema='ANALYTICS',
      unique_key='account_id',
      strategy='check',
      check_cols=['customer_id', 'account_type', 'balance']
    )
}}

SELECT * FROM {{ ref('staging_accounts') }}

{% endsnapshot %}