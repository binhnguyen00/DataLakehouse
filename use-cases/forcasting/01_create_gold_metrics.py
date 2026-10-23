#!/usr/bin/env python3
"""
Step 1: Extract & Aggregate Data into Gold Iceberg Table via Trino
==================================================================
This script pushes down the heavy aggregation computation to Trino/Iceberg:
- Filters 3.7+ million raw records for January 2026.
- Removes invalid trips (non-positive distance or fare).
- Truncates timestamps to hourly intervals (multi-seasonality grain).
- Creates/updates `lakehouse.gold.hourly_taxi_demand` table in Iceberg.
- Exports the clean hourly time series to `data/hourly_taxi_demand.csv`.
"""

import sys
import pandas as pd
from config import (
    ensure_directories,
    get_trino_connection,
    SOURCE_SCHEMA,
    SOURCE_TABLE,
    GOLD_SCHEMA,
    HOURLY_DEMAND_TABLE,
    DATA_DIR,
)

def run():
    print("=" * 70)
    print("STEP 1: CREATING GOLD HOURLY TIME-SERIES TABLE IN LAKEHOUSE")
    print("=" * 70)
    ensure_directories()

    conn = get_trino_connection(schema=GOLD_SCHEMA)
    cursor = conn.cursor()

    full_source = f"lakehouse.{SOURCE_SCHEMA}.{SOURCE_TABLE}"
    full_target = f"lakehouse.{GOLD_SCHEMA}.{HOURLY_DEMAND_TABLE}"

    print(f"[*] Ensuring schema `lakehouse.{GOLD_SCHEMA}` exists...")
    cursor.execute(f"CREATE SCHEMA IF NOT EXISTS lakehouse.{GOLD_SCHEMA}")
    cursor.fetchall()

    print(f"[*] Recreating Gold table `{full_target}` from `{full_source}`...")
    cursor.execute(f"DROP TABLE IF EXISTS {full_target}")
    cursor.fetchall()

    ctas_query = f"""
    CREATE TABLE {full_target} AS
    SELECT 
        date_trunc('hour', tpep_pickup_datetime) AS pickup_hour,
        count(*) AS trip_count,
        round(avg(trip_distance), 2) AS avg_distance,
        round(avg(total_amount), 2) AS avg_fare,
        round(sum(total_amount), 2) AS total_revenue
    FROM {full_source}
    WHERE tpep_pickup_datetime >= TIMESTAMP '2026-01-01 00:00:00 UTC'
      AND tpep_pickup_datetime <  TIMESTAMP '2026-02-01 00:00:00 UTC'
      AND trip_distance > 0
      AND total_amount > 0
    GROUP BY 1
    ORDER BY 1
    """
    cursor.execute(ctas_query)
    cursor.fetchall()
    print(f"[+] Successfully materialized `{full_target}` in Lakehouse Iceberg catalog.")

    # Export to local cache for subsequent Python modeling steps
    print(f"[*] Fetching aggregated time series from `{full_target}`...")
    select_query = f"""
    SELECT 
        pickup_hour,
        trip_count,
        avg_distance,
        avg_fare,
        total_revenue
    FROM {full_target}
    ORDER BY pickup_hour
    """
    df = pd.read_sql(select_query, conn)
    conn.close()

    output_csv = DATA_DIR / "hourly_taxi_demand.csv"
    df.to_csv(output_csv, index=False)
    print(f"[+] Saved {len(df)} hourly records to {output_csv}")

    # Summary metrics
    print("\n--- Summary of Extracted Gold Data ---")
    print(f"  • Total hourly periods: {len(df):,} hours")
    print(f"  • Start time:           {df['pickup_hour'].min()}")
    print(f"  • End time:             {df['pickup_hour'].max()}")
    print(f"  • Total trips analyzed: {df['trip_count'].sum():,} trips")
    print(f"  • Total revenue:        ${df['total_revenue'].sum():,.2f}")
    print(f"  • Max hourly trips:     {df['trip_count'].max():,} trips")
    print(f"  • Min hourly trips:     {df['trip_count'].min():,} trips")
    print("=" * 70)
    print("STEP 1 COMPLETE!\n")

if __name__ == "__main__":
    run()
