import unittest
import os
import sys
from tests.conn import Helper

sys.path.insert(0, os.path.dirname(__file__))


class TestTimeTravel(unittest.TestCase):

  def setUp(self):
    self.conn = Helper.get_connection()
    self.cur = Helper.get_cursor(self.conn)
    self.table_name = "lakehouse.default.test_time_travel_metrics"
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
    self.cur.execute(f"""
            CREATE TABLE {self.table_name} (
                metric_name VARCHAR,
                metric_value DOUBLE
            )
            WITH (format = 'PARQUET')
        """)
    self.cur.fetchall()

    # 2. Insert batch 1 -> Snapshot 1
    self.cur.execute(f"INSERT INTO {self.table_name} VALUES ('cpu_usage', 45.5)")
    self.cur.fetchall()

    # Fetch snapshot 1 ID
    catalog, schema, table = self.table_name.split(".")
    self.cur.execute(
        f'SELECT snapshot_id FROM {catalog}.{schema}."{table}$snapshots" ORDER BY'
        " committed_at ASC"
    )
    snapshots = [row[0] for row in self.cur.fetchall()]
    self.assertTrue(len(snapshots) >= 1)
    snapshot_1_id = snapshots[-1]

    # 3. Insert batch 2 -> Snapshot 2
    self.cur.execute(
        f"INSERT INTO {self.table_name} VALUES ('memory_usage', 72.0)"
    )
    self.cur.fetchall()

    # Current count = 2
    self.cur.execute(f"SELECT COUNT(*) FROM {self.table_name}")
    current_count = self.cur.fetchone()[0]
    self.assertEqual(current_count, 2)

    # 4. Time travel query to snapshot 1
    self.cur.execute(
        f"SELECT COUNT(*) FROM {self.table_name} FOR VERSION AS OF"
        f" {snapshot_1_id}"
    )
    historical_count = self.cur.fetchone()[0]
    self.assertEqual(historical_count, 1)


if __name__ == "__main__":
  unittest.main(verbosity=2)
