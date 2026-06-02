"""
test_db_cli.py —— 锁住 library DB 初始化与 CLI 基础行为.

运行：
    cd ~/self-media-pipeline
    python3 tests/test_db_cli.py
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
DB_CLI = PLUGIN_ROOT / "tools" / "db"


class TestLibraryAutoInit(unittest.TestCase):
    """library.server should create schema on first use."""

    def test_get_db_initializes_schema(self):
        import library.server as L

        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "smp.db"
            with mock.patch.object(L, "DB_PATH", db_path):
                with L.get_db() as conn:
                    tables = {
                        r["name"]
                        for r in conn.execute(
                            "SELECT name FROM sqlite_master WHERE type = 'table'"
                        ).fetchall()
                    }

            self.assertIn("articles", tables)
            self.assertIn("drafts", tables)
            self.assertIn("derivatives", tables)
            self.assertIn("publish_log", tables)


class TestDbCli(unittest.TestCase):
    """CLI smoke tests for user-facing commands."""

    def test_stats_works_without_manual_sqlite_init(self):
        result = subprocess.run(
            [sys.executable, str(DB_CLI), "stats"],
            cwd=PLUGIN_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("articles:", result.stdout)
        self.assertIn("drafts:", result.stdout)

    def test_list_drafts_command_exists(self):
        result = subprocess.run(
            [sys.executable, str(DB_CLI), "list-drafts"],
            cwd=PLUGIN_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_list_derivatives_command_exists(self):
        result = subprocess.run(
            [sys.executable, str(DB_CLI), "list-derivatives"],
            cwd=PLUGIN_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
