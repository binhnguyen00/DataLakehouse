import os
import sys
import unittest
from tests.conn import Helper

sys.path.insert(0, os.path.dirname(__file__))


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
    self.cur.execute(f"CREATE SCHEMA lakehouse.{self.schema_name}")
    self.cur.fetchall()

    # 2. Verify schema exists
    self.cur.execute("SHOW SCHEMAS FROM lakehouse")
    schemas = [row[0] for row in self.cur.fetchall()]
    self.assertIn(self.schema_name, schemas)

    # 3. Drop schema
    self.cur.execute(f"DROP SCHEMA lakehouse.{self.schema_name}")
    self.cur.fetchall()

    # 4. Verify schema dropped
    self.cur.execute("SHOW SCHEMAS FROM lakehouse")
    schemas_after = [row[0] for row in self.cur.fetchall()]
    self.assertNotIn(self.schema_name, schemas_after)


if __name__ == "__main__":
  unittest.main(verbosity=2)
