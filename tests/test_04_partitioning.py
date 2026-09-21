import unittest
import os
import sys
from tests.conn import Helper

sys.path.insert(0, os.path.dirname(__file__))


class TestPartitioning(unittest.TestCase):

  def setUp(self):
    self.conn = Helper.get_connection()
    self.cur = Helper.get_cursor(self.conn)
    self.table_name = "lakehouse.default.test_partitioned_orders"
    self.cur.execute(f"DROP TABLE IF EXISTS {self.table_name}")
    self.cur.fetchall()

  def tearDown(self):
    try:
      self.cur.execute(f"DROP TABLE IF EXISTS {self.table_name}")
      self.cur.fetchall()
    finally:
      self.cur.close()
      self.conn.close()

  def test_day_partitioning_and_metadata(self):
    """Test Iceberg day transform partitioning and $partitions metadata inspection."""
    # 1. Create Partitioned Table
    self.cur.execute(f"""
            CREATE TABLE {self.table_name} (
                order_id BIGINT,
                customer_id BIGINT,
                amount DECIMAL(10, 2),
                order_date DATE
            )
            WITH (
                format = 'PARQUET',
                partitioning = ARRAY['day(order_date)']
            )
        """)
    self.cur.fetchall()

    # 2. Insert records across multiple dates
    self.cur.execute(f"""
            INSERT INTO {self.table_name} (order_id, customer_id, amount, order_date)
            VALUES
                (101, 1, 150.00, DATE '2026-04-01'),
                (102, 2, 200.00, DATE '2026-04-01'),
                (103, 1, 350.00, DATE '2026-04-02'),
                (104, 3, 50.00,  DATE '2026-04-03')
        """)
    self.cur.fetchall()

    # 3. Query with partition prune filter
    self.cur.execute(
        f"SELECT COUNT(*) FROM {self.table_name} WHERE order_date = DATE"
        " '2026-04-01'"
    )
    count_day1 = self.cur.fetchone()[0]
    self.assertEqual(count_day1, 2)

    # 4. Check Iceberg partition metadata table
    catalog, schema, table = self.table_name.split(".")
    self.cur.execute(f'SELECT * FROM {catalog}.{schema}."{table}$partitions"')
    partitions = self.cur.fetchall()
    self.assertEqual(len(partitions), 3)


if __name__ == "__main__":
  unittest.main(verbosity=2)
