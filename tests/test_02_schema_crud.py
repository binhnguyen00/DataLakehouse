import os
import sys
import unittest
from tests.conn import Helper
from tests.logger import get_logger

sys.path.insert(0, os.path.dirname(__file__))
logger = get_logger("test_02_schema_crud")


class TestSchemaCRUD(unittest.TestCase):

  def setUp(self):
    self.conn = Helper.get_connection()
    self.cur = Helper.get_cursor(self.conn)
    self.schema_name = "test_schema_ddl"
    self.cur.execute(f"DROP SCHEMA IF EXISTS lakehouse.{self.schema_name}")
    self.cur.fetchall()

  def tearDown(self):
    try:
      self.cur.execute(f"DROP SCHEMA IF EXISTS lakehouse.{self.schema_name}")
      self.cur.fetchall()
    finally:
      self.cur.close()
      self.conn.close()

  def test_create_and_drop_schema(self):
    """Test schema creation, verification, and dropping."""
    # 1. Create schema
    logger.step(1, 4, f"Creating schema 'lakehouse.{self.schema_name}'...")
    logger.sql(f"CREATE SCHEMA lakehouse.{self.schema_name}")
    self.cur.execute(f"CREATE SCHEMA lakehouse.{self.schema_name}")
    self.cur.fetchall()
    logger.success("Schema created successfully!")

    # 2. Verify schema exists
    logger.step(2, 4, "Verifying schema appears in 'SHOW SCHEMAS'...")
    logger.sql("SHOW SCHEMAS FROM lakehouse")
    self.cur.execute("SHOW SCHEMAS FROM lakehouse")
    schemas = [row[0] for row in self.cur.fetchall()]
    self.assertIn(self.schema_name, schemas)
    logger.subitem(f"Schemas list contains '{self.schema_name}'")

    # 3. Drop schema
    logger.step(3, 4, f"Dropping schema 'lakehouse.{self.schema_name}'...")
    logger.sql(f"DROP SCHEMA lakehouse.{self.schema_name}")
    self.cur.execute(f"DROP SCHEMA lakehouse.{self.schema_name}")
    self.cur.fetchall()
    logger.success("Schema dropped successfully!")

    # 4. Verify schema dropped
    logger.step(4, 4, "Verifying schema no longer exists...")
    self.cur.execute("SHOW SCHEMAS FROM lakehouse")
    schemas_after = [row[0] for row in self.cur.fetchall()]
    self.assertNotIn(self.schema_name, schemas_after)
    logger.success("Schema cleanup verified!")


if __name__ == "__main__":
  unittest.main(verbosity=2)
