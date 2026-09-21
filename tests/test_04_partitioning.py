import os
import sys
import unittest
from tests.conn import Helper
from tests.logger import get_logger

sys.path.insert(0, os.path.dirname(__file__))
logger = get_logger("test_04_partitioning")


class TestPartitioning(unittest.TestCase):

  def setUp(self):
    self.conn = Helper.get_connection()
    self.cur = Helper.get_cursor(self.conn)
    self.table_name = "lakehouse.default.test_partitioned_orders"
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

  def test_day_partitioning_and_metadata(self):
    """Test Iceberg day transform partitioning and $partitions metadata inspection."""
    # 1. Create Partitioned Table
    logger.step(
        1, 4, f"Creating day-partitioned Iceberg table '{self.table_name}'..."
    )
    create_sql = f"""
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
        """
    logger.sql(create_sql)
    self.cur.execute(create_sql)
    self.cur.fetchall()
    logger.success("Partitioned table created.")

    # 2. Insert records across multiple dates
    logger.step(2, 4, "Inserting records spanning 3 distinct calendar dates...")
    insert_sql = f"""
            INSERT INTO {self.table_name} (order_id, customer_id, amount, order_date)
            VALUES
                (101, 1, 150.00, DATE '2026-04-01'),
                (102, 2, 200.00, DATE '2026-04-01'),
                (103, 1, 350.00, DATE '2026-04-02'),
                (104, 3, 50.00,  DATE '2026-04-03')
        """
    logger.sql(insert_sql)
    self.cur.execute(insert_sql)
    self.cur.fetchall()
    logger.success("Inserted records across 2026-04-01, 04-02, 04-03.")

    # 3. Query with partition prune filter
    logger.step(
        3, 4, "Querying with partition filter (order_date = '2026-04-01')..."
    )
    query_sql = (
        f"SELECT COUNT(*) FROM {self.table_name} WHERE order_date = DATE"
        " '2026-04-01'"
    )
    logger.sql(query_sql)
    self.cur.execute(query_sql)
    count_day1 = self.cur.fetchone()[0]
    self.assertEqual(count_day1, 2)
    logger.success(
        f"Partition filter verified (matched {count_day1} rows for"
        " 2026-04-01)!"
    )

    # 4. Check Iceberg partition metadata table
    logger.step(4, 4, "Inspecting Iceberg '$partitions' metadata table...")
    catalog, schema, table = self.table_name.split(".")
    meta_sql = f'SELECT * FROM {catalog}.{schema}."{table}$partitions"'
    logger.sql(meta_sql)
    self.cur.execute(meta_sql)
    partitions = self.cur.fetchall()
    logger.subitem(f"Found {len(partitions)} physical partitions in metadata.")
    self.assertEqual(len(partitions), 3)
    logger.success("Iceberg day partitioning metadata verified!")


if __name__ == "__main__":
  unittest.main(verbosity=2)
