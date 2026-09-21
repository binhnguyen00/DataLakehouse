import os
import sys
import time
import unittest

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


class CleanTestResult(unittest.TestResult):

  def __init__(self, stream=sys.stdout):
    super().__init__()
    self.stream = stream
    self.test_start = None

  def startTest(self, test):
    super().startTest(test)
    self.test_start = time.time()

  def _format_name(self, test):
    # e.g. "test_lakehouse_catalog_exists (test_01_connection.TestLakehouseConnection...)"
    test_id = test.id().split(".")
    # format: test_01_connection.TestClass -> test_01_connection :: test_name
    module_name = test_id[1] if len(test_id) > 2 else test_id[0]
    method_name = test_id[-1]
    # Clean name without prefix 'test_'
    clean_method = method_name
    return f"{module_name} > {clean_method}"

  def addSuccess(self, test):
    super().addSuccess(test)
    elapsed = time.time() - (self.test_start or time.time())
    name = self._format_name(test)
    self.stream.write(
        f"  {GREEN}✓{RESET} {name:<60} {GREEN}PASS{RESET} {DIM}({elapsed:.2f}s){RESET}\n"
    )
    self.stream.flush()

  def addFailure(self, test, err):
    super().addFailure(test, err)
    elapsed = time.time() - (self.test_start or time.time())
    name = self._format_name(test)
    self.stream.write(
        f"  {RED}✗{RESET} {name:<60} {RED}{BOLD}FAIL{RESET} {DIM}({elapsed:.2f}s){RESET}\n"
    )
    self.stream.flush()

  def addError(self, test, err):
    super().addError(test, err)
    elapsed = time.time() - (self.test_start or time.time())
    name = self._format_name(test)
    self.stream.write(
        f"  {RED}✗{RESET} {name:<60} {RED}{BOLD}ERROR{RESET} {DIM}({elapsed:.2f}s){RESET}\n"
    )
    self.stream.flush()


def run_tests():
  test_dir = os.path.dirname(__file__)
  suite = unittest.defaultTestLoader.discover(
      test_dir, pattern="test_*.py"
  )

  print(f"\n{BOLD}{CYAN}=== Lakehouse Iceberg Test Suite ==={RESET}\n")
  runner_start = time.time()
  result = CleanTestResult()
  suite.run(result)
  total_time = time.time() - runner_start

  print(f"\n{DIM}{'-' * 76}{RESET}")
  passed = result.testsRun - len(result.failures) - len(result.errors)
  if result.wasSuccessful():
    print(
        f"{GREEN}{BOLD}ALL PASSED{RESET}  {passed}/{result.testsRun} tests in"
        f" {total_time:.2f}s\n"
    )
    return 0
  else:
    print(
        f"{RED}{BOLD}TESTS FAILED{RESET}  ({len(result.failures)} failed,"
        f" {len(result.errors)} errors) in {total_time:.2f}s\n"
    )
    for test, traceback in result.failures + result.errors:
      print(f"{RED}{BOLD}--- Error in {test.id()} ---{RESET}\n{traceback}\n")
    return 1


if __name__ == "__main__":
  sys.exit(run_tests())
