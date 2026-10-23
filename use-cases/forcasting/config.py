import os
from pathlib import Path
from dotenv import load_dotenv
from trino.dbapi import connect

# Load environment variables if available
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Trino Connection Config
TRINO_HOST = os.getenv("TRINO_HOST", "localhost")
TRINO_PORT = int(os.getenv("TRINO_PORT", "8080"))
TRINO_USER = os.getenv("TRINO_USER", "tester")
TRINO_CATALOG = os.getenv("TRINO_CATALOG", "lakehouse")

# Schemas and Tables
SOURCE_SCHEMA = "samples"
SOURCE_TABLE = "samples"
GOLD_SCHEMA = "gold"
HOURLY_DEMAND_TABLE = "hourly_taxi_demand"
FORECAST_TABLE = "taxi_demand_forecast"

# File Storage Paths
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"

def ensure_directories():
    """Ensure data and reports directories exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

def get_trino_connection(schema=None):
    """Create and return a Trino connection."""
    return connect(
        host=TRINO_HOST,
        port=TRINO_PORT,
        user=TRINO_USER,
        catalog=TRINO_CATALOG,
        schema=schema or GOLD_SCHEMA,
    )
