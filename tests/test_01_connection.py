import os
import sys
import unittest
from tests.conn import Helper
from tests.logger import get_logger

sys.path.insert(0, os.path.dirname(__file__))
logger = get_logger("test_01_connection")


class TestLakehouseConnection(unittest.TestCase):

  def setUp(self):
    self.conn = Helper.get_connection()
    self.cur = Helper.get_cursor(self.conn)

  def tearDown(self):
    self.cur.close()
    self.conn.close()

  def test_lakehouse_catalog_exists(self):
    """Test connection and verify 'lakehouse' catalog is registered in Trino."""
    logger.step(1, 2, "Querying registered catalogs in Trino...")
    logger.sql("SHOW CATALOGS")
    self.cur.execute("SHOW CATALOGS")
    catalogs = [row[0] for row in self.cur.fetchall()]
    logger.subitem(f"Discovered catalogs: {catalogs}")

    logger.step(2, 2, "Verifying 'lakehouse' Iceberg catalog presence...")
    self.assertIn(
        "lakehouse", catalogs, f"Catalog 'lakehouse' not found in {catalogs}"
    )
    logger.success("'lakehouse' catalog is successfully registered!")

  def test_show_schemas(self):
    """Test listing schemas inside the 'lakehouse' catalog."""
    logger.step(1, 2, "Listing schemas from 'lakehouse' catalog...")
    logger.sql("SHOW SCHEMAS FROM lakehouse")
    self.cur.execute("SHOW SCHEMAS FROM lakehouse")
    schemas = [row[0] for row in self.cur.fetchall()]
    logger.subitem(f"Schemas found: {schemas}")

    logger.step(2, 2, "Verifying standard schemas exist...")
    self.assertTrue(
        "default" in schemas or "information_schema" in schemas,
        f"Unexpected schemas: {schemas}",
    )
    logger.success("Lakehouse catalog schema list verified!")


if __name__ == "__main__":
  unittest.main(verbosity=2)
