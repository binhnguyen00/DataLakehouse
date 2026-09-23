import os
import trino


class Helper:
  DEFAULT_CATALOG = os.getenv("TRINO_CATALOG", "lakehouse")
  DEFAULT_SCHEMA = os.getenv("TRINO_SCHEMA", "default")
  DEFAULT_HOST = os.getenv("TRINO_HOST", "localhost")
  DEFAULT_PORT = int(os.getenv("TRINO_PORT", "8080"))
  DEFAULT_USER = os.getenv("TRINO_USER", "tester")

  @classmethod
  def get_connection(
    cls,
    host: str = None,
    port: int = None,
    user: str = None,
    catalog: str = None,
    schema: str = None,
  ) -> trino.dbapi.Connection:
    return trino.dbapi.connect(
      host=host if host is not None else cls.DEFAULT_HOST,
      port=port if port is not None else cls.DEFAULT_PORT,
      user=user if user is not None else cls.DEFAULT_USER,
      catalog=catalog if catalog is not None else cls.DEFAULT_CATALOG,
      schema=schema if schema is not None else cls.DEFAULT_SCHEMA,
    )

  @classmethod
  def get_cursor(cls, conn: trino.dbapi.Connection = None) -> trino.dbapi.Cursor:
    connection = conn or cls.get_connection()
    return connection.cursor()
