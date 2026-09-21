import os
import trino


class Helper:
  def __init__(self):
    DEFAULT_CATALOG   = os.getenv("TRINO_CATALOG", "lakehouse")
    DEFAULT_SCHEMA    = os.getenv("TRINO_SCHEMA", "default")
    DEFAULT_HOST      = os.getenv("TRINO_HOST", "localhost")
    DEFAULT_PORT      = int(os.getenv("TRINO_PORT", "8080"))
    DEFAULT_USER      = os.getenv("TRINO_USER", "tester")

  @classmethod
  def get_connection(
    cls,
    host: str = None,
    port: int = None,
    user: str = None,
    catalog: str = None,
    schema: str = None,
  ) -> trino.dbapi.Connection:
    if host is None:
      host = os.getenv("TRINO_HOST", "localhost")
    if port is None:
      port = int(os.getenv("TRINO_PORT", "8080"))
    if user is None:
      user = os.getenv("TRINO_USER", "tester")
    if catalog is None:
      catalog = os.getenv("TRINO_CATALOG", "lakehouse")
    if schema is None:
      schema = os.getenv("TRINO_SCHEMA", "default")

    return trino.dbapi.connect(
      host=host,
      port=port,
      user=user,
      catalog=catalog,
      schema=schema,
    )

  @classmethod
  def get_cursor(cls, conn: trino.dbapi.Connection = None) -> trino.dbapi.Cursor:
    connection = conn or cls.get_connection()
    return connection.cursor()
