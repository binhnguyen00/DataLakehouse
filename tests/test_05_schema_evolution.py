import os
import sys
import unittest
from tests.conn import Helper
from tests.logger import get_logger

sys.path.insert(0, os.path.dirname(__file__))
logger = get_logger("test_05_schema_evolution")


class TestSchemaEvolution(unittest.TestCase):

  def setUp(self):
    self.conn = Helper.get_connection()
    self.cur = Helper.get_cursor(self.conn)
    self.table_name = "lakehouse.default.test_schema_evolution"
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

  def test_add_column_schema_evolution(self):
    """Test Iceberg schema evolution by adding a new column."""
    # 1. Create Initial Table
    logger.step(1, 5, f"Creating initial table '{self.table_name}' (v1)...")
    create_sql = f"""
            CREATE TABLE {self.table_name} (
                id BIGINT,
                username VARCHAR
            )
            WITH (format = 'PARQUET')
        """
    logger.sql(create_sql)
    self.cur.execute(create_sql)
    self.cur.fetchall()
    logger.success("Table v1 created.")

    # 2. Insert v1 record
    logger.step(2, 5, "Inserting v1 record (without email)...")
    v1_sql = (
        f"INSERT INTO {self.table_name} (id, username) VALUES (1, 'john_doe')"
    )
    logger.sql(v1_sql)
    self.cur.execute(v1_sql)
    self.cur.fetchall()
    logger.success("Inserted row 1 (v1).")

    # 3. Alter Table: Add column
    logger.step(3, 5, "Evolving schema: adding column 'email VARCHAR'...")
    alter_sql = f"ALTER TABLE {self.table_name} ADD COLUMN email VARCHAR"
    logger.sql(alter_sql)
    self.cur.execute(alter_sql)
    self.cur.fetchall()
    logger.success("Schema evolved without rewriting existing parquet files!")

    # 4. Insert v2 record
    logger.step(4, 5, "Inserting v2 record (with email populated)...")
    v2_sql = f"""
            INSERT INTO {self.table_name} (id, username, email)
            VALUES (2, 'jane_doe', 'jane@example.com')
        """
    logger.sql(v2_sql)
    self.cur.execute(v2_sql)
    self.cur.fetchall()
    logger.success("Inserted row 2 (v2).")

    # 5. Query and verify backward compatibility
    logger.step(
        5, 5, "Verifying backward compatibility across schema versions..."
    )
    query_sql = (
        f"SELECT id, username, email FROM {self.table_name} ORDER BY id ASC"
    )
    logger.sql(query_sql)
    self.cur.execute(query_sql)
    rows = self.cur.fetchall()
    logger.subitem(f"Row 1 (v1 data, email=NULL): {rows[0]}")
    logger.subitem(f"Row 2 (v2 data, email present): {rows[1]}")
    self.assertEqual(rows[0], [1, "john_doe", None])
    self.assertEqual(rows[1], [2, "jane_doe", "jane@example.com"])
    logger.success("Schema evolution & backward compatibility verified!")


if __name__ == "__main__":
  unittest.main(verbosity=2)
