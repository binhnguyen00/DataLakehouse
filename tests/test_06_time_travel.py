import os
import sys
import unittest
from tests.conn import Helper
from tests.logger import get_logger

sys.path.insert(0, os.path.dirname(__file__))
logger = get_logger("test_06_time_travel")


class TestTimeTravel(unittest.TestCase):

  def setUp(self):
    self.conn = Helper.get_connection()
    self.cur = Helper.get_cursor(self.conn)
    self.table_name = "lakehouse.default.test_time_travel_metrics"
    self.cur.execute("CREATE SCHEMA IF NOT EXISTS lakehouse.default")
    self.cur.fetchall()
    self.cur.execute(f"DROP TABLE IF EXISTS {self.table_name}")
    self.cur.fetchall()

  def tearDown(self):
    try:
      self.cur.execute(f"DROP TABLE IF EXISTS {self.table_name}")
      self.cur.fetchall()
    finally:
      self.cur.close()
      self.conn.close()

  def test_iceberg_snapshots_and_time_travel(self):
    """Test Iceberg snapshot history and time travel query with FOR VERSION AS OF."""
    # 1. Create table
    logger.step(1, 4, f"Creating Iceberg table '{self.table_name}'...")
    create_sql = f"""
            CREATE TABLE {self.table_name} (
                metric_name VARCHAR,
                metric_value DOUBLE
            )
            WITH (format = 'PARQUET')
        """
    logger.sql(create_sql)
    self.cur.execute(create_sql)
    self.cur.fetchall()
    logger.success("Table created.")

    # 2. Insert batch 1 -> Snapshot 1
    logger.step(2, 4, "Inserting batch 1 -> creates Snapshot 1...")
    insert_1_sql = (
        f"INSERT INTO {self.table_name} VALUES ('cpu_usage', 45.5)"
    )
    logger.sql(insert_1_sql)
    self.cur.execute(insert_1_sql)
    self.cur.fetchall()

    # Fetch snapshot 1 ID
    catalog, schema, table = self.table_name.split(".")
    meta_sql = (
        f'SELECT snapshot_id FROM {catalog}.{schema}."{table}$snapshots"'
        " ORDER BY committed_at ASC"
    )
    self.cur.execute(meta_sql)
    snapshots = [row[0] for row in self.cur.fetchall()]
    self.assertTrue(len(snapshots) >= 1)
    snapshot_1_id = snapshots[-1]
    logger.subitem(f"Snapshot 1 ID: {snapshot_1_id}")

    # 3. Insert batch 2 -> Snapshot 2
    logger.step(3, 4, "Inserting batch 2 -> creates Snapshot 2...")
    insert_2_sql = (
        f"INSERT INTO {self.table_name} VALUES ('memory_usage', 72.0)"
    )
    logger.sql(insert_2_sql)
    self.cur.execute(insert_2_sql)
    self.cur.fetchall()

    self.cur.execute(f"SELECT COUNT(*) FROM {self.table_name}")
    current_count = self.cur.fetchone()[0]
    logger.subitem(f"Current state row count = {current_count}")
    self.assertEqual(current_count, 2)

    # 4. Time travel query to snapshot 1
    logger.step(
        4,
        4,
        f"Querying historical state using 'FOR VERSION AS OF {snapshot_1_id}'...",
    )
    time_travel_sql = (
        f"SELECT COUNT(*) FROM {self.table_name} FOR VERSION AS OF"
        f" {snapshot_1_id}"
    )
    logger.sql(time_travel_sql)
    self.cur.execute(time_travel_sql)
    historical_count = self.cur.fetchone()[0]
    self.assertEqual(historical_count, 1)
    logger.success(
        f"Time travel query verified (Snapshot {snapshot_1_id} row count ="
        f" {historical_count})!"
    )


if __name__ == "__main__":
  unittest.main(verbosity=2)
