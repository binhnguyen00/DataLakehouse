import logging
import sys
import time
from typing import Optional

# ANSI Colors
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"
RED = "\033[31m"


class LakehouseFormatter(logging.Formatter):
  """Custom formatter with timestamps, colors, and structured prefixes."""

  TAG_MAP = {
      logging.DEBUG: f"{DIM}[DEBUG]{RESET}",
      logging.INFO: f"{CYAN}[INFO]{RESET} ",
      logging.WARNING: f"{YELLOW}[WARN]{RESET} ",
      logging.ERROR: f"{RED}[ERROR]{RESET}",
      logging.CRITICAL: f"{RED}{BOLD}[CRIT]{RESET} ",
  }

  def format(self, record: logging.LogRecord) -> str:
    timestamp = time.strftime("%H:%M:%S", time.localtime(record.created))
    prefix = self.TAG_MAP.get(record.levelno, f"[{record.levelname}]")
    return f"{DIM}{timestamp}{RESET} {prefix} {record.getMessage()}"


class LakehouseLogger(logging.Logger):
  """Logger with specialized helper methods for database and lakehouse testing."""

  def step(self, step_no: int, total: int, description: str):
    self.info(f"{BOLD}{BLUE}▶ [{step_no}/{total}]{RESET} {description}")

  def sql(self, query: str):
    # Flatten whitespace for single line or keep compact
    compact_sql = " ".join(query.strip().split())
    if len(compact_sql) > 120:
      compact_sql = compact_sql[:117] + "..."
    self.info(f"{MAGENTA}⚡ SQL:{RESET} {DIM}{compact_sql}{RESET}")

  def success(self, message: str):
    self.info(f"{GREEN}✔ {message}{RESET}")

  def subitem(self, message: str):
    self.info(f"  {DIM}└─{RESET} {message}")


logging.setLoggerClass(LakehouseLogger)


def get_logger(name: str = "lakehouse-tests") -> LakehouseLogger:
  logger = logging.getLogger(name)  # type: ignore
  if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(LakehouseFormatter())
    logger.addHandler(handler)
    logger.propagate = False
  return logger  # type: ignore
