import os
import sys
import unittest
from tests.conn import Helper
from tests.logger import get_logger

sys.path.insert(0, os.path.dirname(__file__))
logger = get_logger("test_03_table_crud")


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
    logger.step(1, 5, f"Creating Iceberg table '{self.table_name}'...")
    create_sql = f"""
            CREATE TABLE {self.table_name} (
                id BIGINT,
                name VARCHAR,
                price DECIMAL(10, 2),
                status VARCHAR
            )
            WITH (format = 'PARQUET')
        """
    logger.sql(create_sql)
    self.cur.execute(create_sql)
    self.cur.fetchall()
    logger.success("Table created successfully!")

    # 2. Insert records
    logger.step(2, 5, "Inserting 3 sample product records...")
    insert_sql = f"""
            INSERT INTO {self.table_name} (id, name, price, status)
            VALUES
                (1, 'Laptop', 1200.00, 'in_stock'),
                (2, 'Mouse', 25.50, 'in_stock'),
                (3, 'Keyboard', 75.00, 'out_of_stock')
        """
    logger.sql(insert_sql)
    self.cur.execute(insert_sql)
    self.cur.fetchall()
    logger.success("Inserted 3 records.")

    # 3. Read & Verify Count
    logger.step(3, 5, "Verifying row count equals 3...")
    self.cur.execute(f"SELECT COUNT(*) FROM {self.table_name}")
    count = self.cur.fetchone()[0]
    self.assertEqual(count, 3)
    logger.subitem(f"Current row count = {count}")

    # 4. Update row (ACID update)
    logger.step(4, 5, "Performing ACID UPDATE on id=2...")
    update_sql = f"UPDATE {self.table_name} SET status = 'low_stock' WHERE id = 2"
    logger.sql(update_sql)
    self.cur.execute(update_sql)
    self.cur.fetchall()

    self.cur.execute(f"SELECT status FROM {self.table_name} WHERE id = 2")
    updated_status = self.cur.fetchone()[0]
    self.assertEqual(updated_status, "low_stock")
    logger.success(f"Row updated: status='{updated_status}' verified!")

    # 5. Delete row (ACID delete)
    logger.step(5, 5, "Performing ACID DELETE on id=3...")
    delete_sql = f"DELETE FROM {self.table_name} WHERE id = 3"
    logger.sql(delete_sql)
    self.cur.execute(delete_sql)
    self.cur.fetchall()

    self.cur.execute(f"SELECT COUNT(*) FROM {self.table_name}")
    count_after_del = self.cur.fetchone()[0]
    self.assertEqual(count_after_del, 2)
    logger.success(f"Row deleted: remaining count = {count_after_del} verified!")


if __name__ == "__main__":
  unittest.main(verbosity=2)
