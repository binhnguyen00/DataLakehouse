#!/usr/bin/env python3
"""
Master Pipeline Runner: End-to-End Time Series Forecasting
==========================================================
Executes all steps sequentially:
  1. `01_create_gold_metrics.py`: Aggregate raw Lakehouse data into Gold Iceberg table.
  2. `02_eda_timeseries.py`: Perform EDA and generate seasonality charts.
  3. `03_train_forecast_model.py`: Train Prophet model, evaluate metrics, and predict.
  4. `04_publish_to_lakehouse.py`: Materialize predictions back into Iceberg for Superset BI.
"""

import time
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

STEPS = [
    ("Step 1: Extract Gold Metrics", BASE_DIR / "01_create_gold_metrics.py"),
    ("Step 2: EDA & Seasonality Profiling", BASE_DIR / "02_eda_timeseries.py"),
    ("Step 3: Train Forecast Model", BASE_DIR / "03_train_forecast_model.py"),
    ("Step 4: Publish Forecast to Lakehouse", BASE_DIR / "04_publish_to_lakehouse.py"),
]


def main():
  start_total = time.time()
  print("=" * 80)
  print("STARTING FULL END-TO-END TIME SERIES FORECASTING PIPELINE")
  print("=" * 80)

  for idx, (title, script_path) in enumerate(STEPS, start=1):
    step_start = time.time()
    print(f"\n[>>>] Running {title} ({script_path.name})...")
    res = subprocess.run([sys.executable, str(script_path)], cwd=str(BASE_DIR))
    if res.returncode != 0:
      print(f"[!] {title} failed with exit code {res.returncode}. Aborting pipeline.")
      sys.exit(res.returncode)
    elapsed = time.time() - step_start
    print(f"[OK] {title} finished in {elapsed:.2f}s.")

  total_elapsed = time.time() - start_total
  print("\n" + "=" * 80)
  print(f"PIPELINE COMPLETED SUCCESSFULLY IN {total_elapsed:.2f}s!")
  print("=" * 80)


if __name__ == "__main__":
  main()
