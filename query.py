import trino

# Connect to Trino
# Adjust the host and port if your Trino server is running elsewhere
conn = trino.dbapi.connect(
  host="localhost",
  port=8080,
  user="python_user",
  catalog="minio",
  schema="default",
)

cur = conn.cursor()

try:
  # 1. Create the schema
  print("Creating schema 'default' in 'minio' catalog if it doesn't exist...")
  cur.execute("CREATE SCHEMA IF NOT EXISTS minio.default")
  # fetchall to consume the result if any
  cur.fetchall()

  # 2. Create the table
  print("Creating table 'users' if it doesn't exist...")
  cur.execute("""
      CREATE TABLE IF NOT EXISTS minio.default.users (
          id BIGINT,
          name VARCHAR,
          email VARCHAR,
          created_at TIMESTAMP(6) WITH TIME ZONE
      )
      WITH (
          format = 'PARQUET',
          partitioning = ARRAY['day(created_at)']
      )
  """)
  cur.fetchall()

  # 3. Insert some data so it's not empty
  print("Inserting a sample row...")
  cur.execute("""
      INSERT INTO minio.default.users (id, name, email, created_at)
      VALUES (1, 'Alice from Python', 'alice@example.com', current_timestamp)
  """)
  cur.fetchall()

  print("\nExecuting query: SELECT * FROM minio.default.users")
  cur.execute("SELECT * FROM minio.default.users")

  # Fetch the column names
  columns = [desc[0] for desc in cur.description]
  print(f"Columns: {columns}")

  # Fetch all rows
  rows = cur.fetchall()

  print("\nResults:")
  for row in rows:
    print(row)

except Exception as e:
  print(f"An error occurred: {e}")
finally:
  cur.close()
  conn.close()
