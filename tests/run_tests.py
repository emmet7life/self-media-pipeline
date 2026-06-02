#!/usr/bin/env python3
"""
run_tests.py —— 一键跑 self-media-pipeline 的所有 unit tests

设计原则:
- 0 外部依赖（仅用 stdlib 的 unittest + subprocess）
- 显示每个 test file 的 pass/fail 摘要
- CI-friendly: 失败时 exit code != 0

用法:
    python3 tests/run_tests.py
    python3 tests/run_tests.py --verbose
    python3 tests/run_tests.py tests/test_render.py  # 只跑指定文件
"""
import argparse
import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
PLUGIN_ROOT = TESTS_DIR.parent


def main() -> int:
    ap = argparse.ArgumentParser(description="Run self-media-pipeline unit tests")
    ap.add_argument(
        "test_files",
        nargs="*",
        help="Specific test file(s) to run (default: all under tests/)",
    )
    ap.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    ap.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI color codes (for CI logs)",
    )
    args = ap.parse_args()

    # 把 plugin 根加进 sys.path，让 tests/ 作为包被找到
    sys.path.insert(0, str(PLUGIN_ROOT))

    color = not args.no_color and sys.stdout.isatty()
    RED = "\033[91m" if color else ""
    GREEN = "\033[92m" if color else ""
    YELLOW = "\033[93m" if color else ""
    BOLD = "\033[1m" if color else ""
    RESET = "\033[0m" if color else ""

    # 决定跑哪些 test files
    if args.test_files:
        test_paths = [Path(p) for p in args.test_files]
    else:
        test_paths = sorted(TESTS_DIR.glob("test_*.py"))

    if not test_paths:
        print(f"{YELLOW}no test files found in {TESTS_DIR}{RESET}")
        return 0

    print(f"{BOLD}Running {len(test_paths)} test file(s){RESET}")
    print(f"  Plugin root: {PLUGIN_ROOT}")
    print()

    total_tests = 0
    total_failures = 0
    total_errors = 0
    file_results = []

    for tp in test_paths:
        if not tp.exists():
            print(f"{RED}  [MISS] {tp}{RESET}")
            continue

        # 加载 test module
        module_name = "tests." + tp.stem if tp.parent.name == "tests" else tp.stem
        loader = unittest.TestLoader()
        try:
            suite = loader.loadTestsFromName(module_name)
        except (ImportError, ModuleNotFoundError) as e:
            print(f"{RED}  [LOAD FAIL] {tp}: {e}{RESET}")
            total_errors += 1
            continue

        # 跑
        runner = unittest.TextTestRunner(verbosity=2 if args.verbose else 1, stream=sys.stdout)
        result = runner.run(suite)

        n_tests = result.testsRun
        n_fail = len(result.failures)
        n_err = len(result.errors)

        total_tests += n_tests
        total_failures += n_fail
        total_errors += n_err

        if n_fail == 0 and n_err == 0:
            status = f"{GREEN}PASS{RESET}"
        else:
            status = f"{RED}FAIL{RESET}"
        file_results.append((tp.name, status, n_tests, n_fail, n_err))
        print()

    # 总结
    print(f"{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}Summary{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}")
    for name, status, n, nf, ne in file_results:
        print(f"  {status}  {name:40s}  {n:3d} tests  {nf} fail  {ne} error")

    print()
    print(f"  {BOLD}Total:{RESET} {total_tests} tests, {total_failures} failures, {total_errors} errors")

    if total_failures == 0 and total_errors == 0:
        print(f"  {GREEN}✓ All tests passed{RESET}")
        return 0
    else:
        print(f"  {RED}✗ Some tests failed{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
