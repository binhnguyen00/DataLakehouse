import os
import sys
import unittest
from tests.conn import Helper

sys.path.insert(0, os.path.dirname(__file__))


class TestLakehouseConnection(unittest.TestCase):

  def setUp(self):
    self.conn = Helper.get_connection()
    self.cur = Helper.get_cursor(self.conn)

  def tearDown(self):
    self.cur.close()
    self.conn.close()

  def test_lakehouse_catalog_exists(self):
    """Test connection and verify 'lakehouse' catalog is registered in Trino."""
    self.cur.execute("SHOW CATALOGS")
    catalogs = [row[0] for row in self.cur.fetchall()]
    self.assertIn(
        "lakehouse", catalogs, f"Catalog 'lakehouse' not found in {catalogs}"
    )

  def test_show_schemas(self):
    """Test listing schemas inside the 'lakehouse' catalog."""
    self.cur.execute("SHOW SCHEMAS FROM lakehouse")
    schemas = [row[0] for row in self.cur.fetchall()]
    self.assertTrue(
        "default" in schemas or "information_schema" in schemas,
        f"Unexpected schemas: {schemas}",
    )


if __name__ == "__main__":
  unittest.main(verbosity=2)
