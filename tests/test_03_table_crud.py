import os
import sys
import unittest
from tests.conn import Helper

sys.path.insert(0, os.path.dirname(__file__))


class TestTableCRUD(unittest.TestCase):

  def setUp(self):
    self.conn = Helper.get_connection()
    self.cur = Helper.get_cursor(self.conn)
    self.table_name = "lakehouse.default.test_crud_products"
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

  def test_iceberg_table_lifecycle_and_acid(self):
    """Test Iceberg table creation, insert, update, delete, and drop."""
    # 1. Create table
    self.cur.execute(f"""
            CREATE TABLE {self.table_name} (
                id BIGINT,
                name VARCHAR,
                price DECIMAL(10, 2),
                status VARCHAR
            )
            WITH (format = 'PARQUET')
        """)
    self.cur.fetchall()

    # 2. Insert records
    self.cur.execute(f"""
            INSERT INTO {self.table_name} (id, name, price, status)
            VALUES
                (1, 'Laptop', 1200.00, 'in_stock'),
                (2, 'Mouse', 25.50, 'in_stock'),
                (3, 'Keyboard', 75.00, 'out_of_stock')
        """)
    self.cur.fetchall()

    # 3. Read & Verify Count
    self.cur.execute(f"SELECT COUNT(*) FROM {self.table_name}")
    count = self.cur.fetchone()[0]
    self.assertEqual(count, 3)

    # 4. Update row (ACID update)
    self.cur.execute(
        f"UPDATE {self.table_name} SET status = 'low_stock' WHERE id = 2"
    )
    self.cur.fetchall()

    self.cur.execute(f"SELECT status FROM {self.table_name} WHERE id = 2")
    updated_status = self.cur.fetchone()[0]
    self.assertEqual(updated_status, "low_stock")

    # 5. Delete row (ACID delete)
    self.cur.execute(f"DELETE FROM {self.table_name} WHERE id = 3")
    self.cur.fetchall()

    self.cur.execute(f"SELECT COUNT(*) FROM {self.table_name}")
    count_after_del = self.cur.fetchone()[0]
    self.assertEqual(count_after_del, 2)


if __name__ == "__main__":
  unittest.main(verbosity=2)
