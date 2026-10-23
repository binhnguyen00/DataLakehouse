#!/usr/bin/env python3
"""
Step 3: Train Prophet Model & Evaluate Time-Series Forecast
===========================================================
This script trains a Meta Prophet forecasting model on the hourly taxi demand:
- Formats time series for Prophet (`ds` and `y`).
- Splits data chronologically:
    * Train: Jan 01 - Jan 24 (24 days = 576 hours)
    * Test:  Jan 25 - Jan 31 (7 days = 168 hours)
- Configures daily and weekly seasonality + US holidays (New Year, MLK Day).
- Evaluates out-of-sample forecast accuracy: MAE, RMSE, MAPE, R2 score.
- Generates forecast for the test set and next 7 days horizon.
- Saves plots and `reports/forecast_results.csv`.
"""

import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from prophet import Prophet
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score
from config import DATA_DIR, REPORTS_DIR, ensure_directories

# Style settings
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams['font.sans-serif'] = 'Helvetica, Arial, DejaVu Sans'

def run():
    print("=" * 70)
    print("STEP 3: TRAINING PROPHET MODEL & EVALUATING ACCURACY")
    print("=" * 70)
    ensure_directories()

    csv_path = DATA_DIR / "hourly_taxi_demand.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing {csv_path}. Please run `01_create_gold_metrics.py` first.")

    df = pd.read_csv(csv_path)
    # Strip timezone to ensure Prophet runs cleanly
    df['ds'] = pd.to_datetime(df['pickup_hour']).dt.tz_localize(None)
    df['y'] = df['trip_count']

    # Chronological Split
    split_date = pd.Timestamp("2026-01-25 00:00:00")
    train_df = df[df['ds'] < split_date].copy()
    test_df  = df[df['ds'] >= split_date].copy()

    print(f"[*] Total dataset: {len(df)} hours (Jan 01 -> Jan 31, 2026)")
    print(f"[*] Training set:  {len(train_df)} hours (Jan 01 -> Jan 24)")
    print(f"[*] Test set:      {len(test_df)} hours (Jan 25 -> Jan 31, 7 days)")

    # Initialize Prophet Model
    print("\n[*] Initializing & fitting Prophet model...")
    model = Prophet(
        growth='linear',
        daily_seasonality=True,
        weekly_seasonality=True,
        yearly_seasonality=False,
        seasonality_mode='multiplicative',
        interval_width=0.80  # 80% confidence interval
    )
    # Add US Holidays (e.g. New Year's Day, MLK Day)
    model.add_country_holidays(country_name='US')

    model.fit(train_df[['ds', 'y']])
    print("[+] Model fitted successfully.")

    # Predict on Train + Test + 7 Days Future (into Feb 2026)
    total_test_hours = len(test_df)
    future_extra_hours = 7 * 24  # 7 days future horizon
    future = model.make_future_dataframe(periods=total_test_hours + future_extra_hours, freq='h')
    forecast = model.predict(future)

    # Merge forecast with actuals for evaluation
    eval_df = pd.merge(
        forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']],
        df[['ds', 'y']],
        on='ds',
        how='left'
    )
    eval_df['yhat'] = eval_df['yhat'].clip(lower=0)
    eval_df['yhat_lower'] = eval_df['yhat_lower'].clip(lower=0)

    # Tag partitions
    eval_df['split'] = 'future'
    eval_df.loc[eval_df['ds'] < split_date, 'split'] = 'train'
    eval_df.loc[(eval_df['ds'] >= split_date) & (eval_df['ds'] <= df['ds'].max()), 'split'] = 'test'

    # Compute Test Metrics
    test_eval = eval_df[eval_df['split'] == 'test']
    y_true = test_eval['y'].values
    y_pred = test_eval['yhat'].values

    mae = mean_absolute_error(y_true, y_pred)
    rmse = root_mean_squared_error(y_true, y_pred)
    mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
    wape = (np.sum(np.abs(y_true - y_pred)) / np.sum(y_true)) * 100
    r2 = r2_score(y_true, y_pred)

    print("\n" + "=" * 50)
    print("MODEL EVALUATION ON TEST SET (JAN 25 - JAN 31):")
    print(f"  • MAE  (Mean Absolute Error):       {mae:>8.2f} trips/hour")
    print(f"  • RMSE (Root Mean Squared Error):   {rmse:>8.2f} trips/hour")
    print(f"  • WAPE (Weighted Abs Pct Error):    {wape:>8.2f}% (Industry standard)")
    print(f"  • MAPE (Mean Abs Percentage Error): {mape:>8.2f}%")
    print(f"  • R²   (Coefficient of Determination): {r2:>6.4f}")
    print("=" * 50)

    # -------------------------------------------------------------
    # Plot 1: Forecast vs Actual on Test Window
    # -------------------------------------------------------------
    fig, (ax_main, ax_zoom) = plt.subplots(2, 1, figsize=(14, 9), dpi=150, gridspec_kw={'height_ratios': [1, 1.2]})

    # Subplot 1: Full Month Overview
    ax_main.plot(df['ds'], df['y'], color='#333333', linewidth=1.2, label='Actual Demand')
    ax_main.plot(eval_df['ds'], eval_df['yhat'], color='#0072b2', linestyle='--', linewidth=1.5, label='Prophet Forecast')
    ax_main.axvline(split_date, color='#d55e00', linestyle=':', linewidth=2, label='Train / Test Split')
    ax_main.set_title("NYC Yellow Taxi - Hourly Demand Forecast Overview (January 2026)", fontsize=13, fontweight='bold')
    ax_main.set_ylabel("Trips / Hour", fontsize=10, fontweight='bold')
    ax_main.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    ax_main.legend(loc='upper left', frameon=True, facecolor='white')

    # Subplot 2: Zoomed-in 7-Day Test Set (Jan 25 - Jan 31)
    zoom_actual = df[df['ds'] >= split_date]
    zoom_pred = eval_df[eval_df['split'] == 'test']

    ax_zoom.plot(zoom_actual['ds'], zoom_actual['y'], marker='o', markersize=4, color='#111111', linewidth=1.8, label='Actual Ground Truth')
    ax_zoom.plot(zoom_pred['ds'], zoom_pred['yhat'], marker='s', markersize=3, color='#0072b2', linestyle='-', linewidth=2, label=f'Prophet Forecast (MAPE: {mape:.1f}%)')
    ax_zoom.fill_between(
        zoom_pred['ds'],
        zoom_pred['yhat_lower'],
        zoom_pred['yhat_upper'],
        color='#56b4e9',
        alpha=0.35,
        label='80% Confidence Interval'
    )
    ax_zoom.set_title(f"Detailed 7-Day Out-of-Sample Test Evaluation (R² = {r2:.3f}, MAE = {mae:.1f} trips)", fontsize=13, fontweight='bold')
    ax_zoom.set_ylabel("Trips / Hour", fontsize=10, fontweight='bold')
    ax_zoom.set_xlabel("Date & Time", fontsize=10, fontweight='bold')
    ax_zoom.xaxis.set_major_formatter(mdates.DateFormatter('%a %b %d\n%H:00'))
    ax_zoom.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    ax_zoom.legend(loc='upper right', frameon=True, facecolor='white')

    plt.tight_layout()
    chart3_path = REPORTS_DIR / "03_forecast_vs_actual.png"
    plt.savefig(chart3_path)
    plt.close()
    print(f"\n[+] Saved forecast evaluation plot: {chart3_path}")

    # -------------------------------------------------------------
    # Plot 2: Seasonality Components Decomposition
    # -------------------------------------------------------------
    fig_comp = model.plot_components(forecast)
    chart4_path = REPORTS_DIR / "04_seasonality_decomposition.png"
    fig_comp.savefig(chart4_path, dpi=150)
    plt.close()
    print(f"[+] Saved seasonality decomposition: {chart4_path}")

    # Save results to CSV for publishing to Lakehouse
    output_results = REPORTS_DIR / "forecast_results.csv"
    export_df = eval_df.rename(columns={
        'y': 'actual_trips',
        'yhat': 'predicted_trips',
        'yhat_lower': 'lower_bound',
        'yhat_upper': 'upper_bound'
    })[['ds', 'actual_trips', 'predicted_trips', 'lower_bound', 'upper_bound', 'split']]
    export_df.to_csv(output_results, index=False)
    print(f"[+] Saved {len(export_df)} prediction records to {output_results}")

    print("=" * 70)
    print("STEP 3 COMPLETE!\n")

if __name__ == "__main__":
    run()
