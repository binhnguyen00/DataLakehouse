import unittest
import os
import sys
from tests.conn import Helper

sys.path.insert(0, os.path.dirname(__file__))


class TestSchemaEvolution(unittest.TestCase):

  def setUp(self):
    self.conn = Helper.get_connection()
    self.cur = Helper.get_cursor(self.conn)
    self.table_name = "lakehouse.default.test_schema_evolution"
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
    self.cur.execute(f"""
            CREATE TABLE {self.table_name} (
                id BIGINT,
                username VARCHAR
            )
            WITH (format = 'PARQUET')
        """)
    self.cur.fetchall()

    # 2. Insert v1 record
    self.cur.execute(
        f"INSERT INTO {self.table_name} (id, username) VALUES (1, 'john_doe')"
    )
    self.cur.fetchall()

    # 3. Alter Table: Add column
    self.cur.execute(f"ALTER TABLE {self.table_name} ADD COLUMN email VARCHAR")
    self.cur.fetchall()

    # 4. Insert v2 record
    self.cur.execute(f"""
            INSERT INTO {self.table_name} (id, username, email)
            VALUES (2, 'jane_doe', 'jane@example.com')
        """)
    self.cur.fetchall()

    # 5. Query and verify backward compatibility
    self.cur.execute(
        f"SELECT id, username, email FROM {self.table_name} ORDER BY id ASC"
    )
    rows = self.cur.fetchall()
    self.assertEqual(rows[0], [1, "john_doe", None])
    self.assertEqual(rows[1], [2, "jane_doe", "jane@example.com"])


if __name__ == "__main__":
  unittest.main(verbosity=2)
