#!/usr/bin/env python3
"""
Step 4: Publish Forecast Back to Lakehouse for BI Consumption
=============================================================
This script closes the loop of the 5-layer Data Lakehouse architecture:
- Reads the generated forecast dataset (`reports/forecast_results.csv`).
- Connects to Trino via the API layer.
- Materializes an Iceberg table: `lakehouse.gold.taxi_demand_forecast`.
- Allows Apache Superset (Consumption Layer) to query and render:
    * Actual demand vs Forecasted demand
    * 80% Confidence Interval bounds (lower_bound, upper_bound)
    * Real-time drilldowns by split (train, test, future)
"""

import sys
import pandas as pd
import numpy as np
from config import (
    ensure_directories,
    get_trino_connection,
    GOLD_SCHEMA,
    FORECAST_TABLE,
    REPORTS_DIR,
)

def run():
    print("=" * 70)
    print("STEP 4: PUBLISHING FORECAST RESULTS TO LAKEHOUSE (ICEBERG)")
    print("=" * 70)
    ensure_directories()

    csv_path = REPORTS_DIR / "forecast_results.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing {csv_path}. Please run `03_train_forecast_model.py` first.")

    df = pd.read_csv(csv_path)
    df['ds'] = pd.to_datetime(df['ds'])

    conn = get_trino_connection(schema=GOLD_SCHEMA)
    cursor = conn.cursor()

    full_target = f"lakehouse.{GOLD_SCHEMA}.{FORECAST_TABLE}"

    print(f"[*] Recreating target Iceberg table `{full_target}`...")
    cursor.execute(f"DROP TABLE IF EXISTS {full_target}")
    cursor.fetchall()

    create_table_sql = f"""
    CREATE TABLE {full_target} (
        ds TIMESTAMP(6) WITH TIME ZONE,
        actual_trips DOUBLE,
        predicted_trips DOUBLE,
        lower_bound DOUBLE,
        upper_bound DOUBLE,
        split VARCHAR
    )
    """
    cursor.execute(create_table_sql)
    cursor.fetchall()
    print(f"[+] Created Iceberg table `{full_target}`.")

    # Batch insertion into Iceberg via Trino
    batch_size = 150
    total_rows = len(df)
    print(f"[*] Inserting {total_rows} forecast records in batches of {batch_size}...")

    records = []
    for _, row in df.iterrows():
        ts_str = row['ds'].strftime("%Y-%m-%d %H:%M:%S")
        actual_val = "NULL" if pd.isna(row['actual_trips']) else f"{row['actual_trips']:.2f}"
        pred_val = f"{row['predicted_trips']:.2f}"
        lower_val = f"{row['lower_bound']:.2f}"
        upper_val = f"{row['upper_bound']:.2f}"
        split_val = f"'{row['split']}'"

        record_str = f"(TIMESTAMP '{ts_str} UTC', {actual_val}, {pred_val}, {lower_val}, {upper_val}, {split_val})"
        records.append(record_str)

    for i in range(0, total_rows, batch_size):
        chunk = records[i:i + batch_size]
        insert_sql = f"INSERT INTO {full_target} VALUES {', '.join(chunk)}"
        cursor.execute(insert_sql)
        cursor.fetchall()
        print(f"    -> Inserted rows {i + 1} to {min(i + batch_size, total_rows)}...")

    print(f"[+] All {total_rows} records successfully written to Iceberg!")

    # Verify summary from Lakehouse
    verify_query = f"""
    SELECT 
        split,
        count(*) AS record_count,
        round(avg(actual_trips), 1) AS avg_actual,
        round(avg(predicted_trips), 1) AS avg_predicted,
        min(ds) AS start_ts,
        max(ds) AS end_ts
    FROM {full_target}
    GROUP BY split
    ORDER BY min(ds)
    """
    summary_df = pd.read_sql(verify_query, conn)
    conn.close()

    print("\n--- Lakehouse Verification Summary ---")
    for _, row in summary_df.iterrows():
        print(f"  • Split: {row['split']:<6} | Rows: {row['record_count']:>3} | "
              f"Avg Pred: {row['avg_predicted']:>7.1f} | Avg Actual: {str(row['avg_actual']):>7} | "
              f"Time: {str(row['start_ts'])[:10]} to {str(row['end_ts'])[:10]}")

    print("\n" + "=" * 70)
    print("HOW TO VIEW IN SUPERSET (Consumption Layer):")
    print("  1. Open Apache Superset at http://localhost:8088")
    print("  2. Go to 'Data' -> 'Datasets' -> '+ Dataset'")
    print(f"  3. Select Database 'Lakehouse', Schema '{GOLD_SCHEMA}', Table '{FORECAST_TABLE}'")
    print("  4. Create an 'ECharts Timeseries Chart' with:")
    print("     - Time Column: `ds`")
    print("     - Metrics: `AVG(actual_trips)`, `AVG(predicted_trips)`")
    print("     - Dimensions: `split`")
    print("=" * 70)
    print("STEP 4 COMPLETE!\n")

if __name__ == "__main__":
    run()
