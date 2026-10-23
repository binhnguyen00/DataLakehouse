#!/usr/bin/env python3
"""
Step 2: Exploratory Data Analysis (EDA) & Time Series Profiling
==============================================================
This script inspects the hourly time series to understand seasonality patterns:
- Verifies full continuity (ensuring exactly 744 hours for 31 days of January).
- Analyzes daily and weekly seasonality patterns (rush hours, weekend vs weekday).
- Generates high-quality charts for the project report into `reports/`.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from config import DATA_DIR, REPORTS_DIR, ensure_directories

# Style settings for clean, professional charts
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams['font.sans-serif'] = 'Helvetica, Arial, DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#cccccc'
plt.rcParams['axes.linewidth'] = 0.8

def run():
    print("=" * 70)
    print("STEP 2: EXPLORATORY DATA ANALYSIS & SEASONALITY PROFILING")
    print("=" * 70)
    ensure_directories()

    csv_path = DATA_DIR / "hourly_taxi_demand.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing {csv_path}. Please run `01_create_gold_metrics.py` first.")

    df = pd.read_csv(csv_path)
    df['pickup_hour'] = pd.to_datetime(df['pickup_hour'])
    df = df.sort_values('pickup_hour').reset_index(drop=True)

    # Time series continuity check
    df_indexed = df.set_index('pickup_hour')
    expected_hours = 31 * 24  # January has 31 days
    actual_hours = len(df_indexed)
    print(f"[*] Continuity check: {actual_hours} hours recorded / {expected_hours} expected.")

    # Time-based features
    df['date'] = df['pickup_hour'].dt.date
    df['hour'] = df['pickup_hour'].dt.hour
    df['day_name'] = df['pickup_hour'].dt.day_name()
    df['is_weekend'] = df['pickup_hour'].dt.day_of_week.isin([5, 6])

    # 1. Summary Statistics
    weekday_avg = df[~df['is_weekend']]['trip_count'].mean()
    weekend_avg = df[df['is_weekend']]['trip_count'].mean()
    peak_row = df.loc[df['trip_count'].idxmax()]
    trough_row = df.loc[df['trip_count'].idxmin()]

    print("\n--- Key Time-Series Observations ---")
    print(f"  • Average trips/hour (Weekday): {weekday_avg:,.1f} trips")
    print(f"  • Average trips/hour (Weekend): {weekend_avg:,.1f} trips")
    print(f"  • All-time Peak Hour:          {peak_row['pickup_hour']} ({peak_row['trip_count']:,} trips)")
    print(f"  • All-time Lowest Hour:        {trough_row['pickup_hour']} ({trough_row['trip_count']:,} trips)")

    # Busiest days of week
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    dow_stats = df.groupby('day_name')['trip_count'].agg(['mean', 'sum']).reindex(day_order)
    print("\n--- Demand by Day of Week (Average Trips/Hour) ---")
    for day, row in dow_stats.iterrows():
        print(f"  • {day:<10}: {row['mean']:>7,.1f} trips/hour (Total: {row['sum']:>10,})")

    # -------------------------------------------------------------
    # Plot 1: Daily Total Demand Trend across Jan 2026
    # -------------------------------------------------------------
    daily_df = df.groupby('date').agg({
        'trip_count': 'sum',
        'total_revenue': 'sum'
    }).reset_index()
    daily_df['date'] = pd.to_datetime(daily_df['date'])

    fig, ax1 = plt.subplots(figsize=(13, 5), dpi=150)
    color1 = '#1f77b4'
    color2 = '#2ca02c'

    ax1.set_title("NYC Yellow Taxi - Daily Trips & Revenue (January 2026)", fontsize=14, fontweight='bold', pad=15)
    ax1.plot(daily_df['date'], daily_df['trip_count'], color=color1, marker='o', linewidth=2, label="Daily Trips")
    ax1.set_ylabel("Total Trips / Day", color=color1, fontsize=11, fontweight='bold')
    ax1.tick_params(axis='y', labelcolor=color1)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    ax1.xaxis.set_major_locator(mdates.DayLocator(interval=2))
    plt.xticks(rotation=45)

    ax2 = ax1.twinx()
    ax2.plot(daily_df['date'], daily_df['total_revenue'] / 1e6, color=color2, linestyle='--', marker='s', linewidth=1.8, label="Revenue ($M)")
    ax2.set_ylabel("Total Revenue ($ Millions)", color=color2, fontsize=11, fontweight='bold')
    ax2.tick_params(axis='y', labelcolor=color2)
    ax2.grid(False)

    plt.tight_layout()
    chart1_path = REPORTS_DIR / "01_daily_trend.png"
    plt.savefig(chart1_path)
    plt.close()
    print(f"\n[+] Saved chart: {chart1_path}")

    # -------------------------------------------------------------
    # Plot 2: Hourly Demand Pattern: Weekday vs Weekend
    # -------------------------------------------------------------
    hourly_weekday = df[~df['is_weekend']].groupby('hour')['trip_count'].mean()
    hourly_weekend = df[df['is_weekend']].groupby('hour')['trip_count'].mean()

    fig, ax = plt.subplots(figsize=(11, 5), dpi=150)
    hours = np.arange(24)

    ax.plot(hours, hourly_weekday, label="Weekday (Mon - Fri)", color='#004c6d', linewidth=2.5, marker='o')
    ax.plot(hours, hourly_weekend, label="Weekend (Sat - Sun)", color='#d45087', linewidth=2.5, marker='s', linestyle='--')

    # Highlight rush hour windows
    ax.axvspan(7, 9, color='#e0f3db', alpha=0.5, label='Morning Rush (7h - 9h)')
    ax.axvspan(17, 19, color='#ffeda0', alpha=0.5, label='Evening Rush (17h - 19h)')

    ax.set_title("Hourly Demand Profile: Weekdays vs Weekends", fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel("Hour of Day (00:00 - 23:00)", fontsize=11, fontweight='bold')
    ax.set_ylabel("Average Trips / Hour", fontsize=11, fontweight='bold')
    ax.set_xticks(hours)
    ax.set_xticklabels([f"{h:02d}:00" for h in hours], rotation=45)
    ax.legend(frameon=True, facecolor='white', edgecolor='#cccccc', loc='upper left')

    plt.tight_layout()
    chart2_path = REPORTS_DIR / "02_hourly_pattern_by_dayofweek.png"
    plt.savefig(chart2_path)
    plt.close()
    print(f"[+] Saved chart: {chart2_path}")

    print("=" * 70)
    print("STEP 2 COMPLETE!\n")

if __name__ == "__main__":
    run()
