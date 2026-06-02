from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
LIST_TARGETS = PLUGIN_ROOT / "tools" / "list-targets"


class TestListTargets(unittest.TestCase):
    def test_json_marks_active_platforms_selectable(self):
        result = subprocess.run(
            [sys.executable, str(LIST_TARGETS), "--json"],
            cwd=PLUGIN_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = {row["id"]: row for row in json.loads(result.stdout)}
        self.assertEqual(rows["wechat"]["status"], "active")
        self.assertTrue(rows["wechat"]["selectable"])
        self.assertEqual(rows["xiaohongshu"]["status"], "active")
        self.assertTrue(rows["xiaohongshu"]["selectable"])
        self.assertEqual(rows["zhihu"]["status"], "planned")
        self.assertFalse(rows["zhihu"]["selectable"])

    def test_active_only_hides_planned_platforms(self):
        result = subprocess.run(
            [sys.executable, str(LIST_TARGETS), "--active-only", "--json"],
            cwd=PLUGIN_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        platform_ids = {row["id"] for row in json.loads(result.stdout)}
        self.assertEqual(platform_ids, {"wechat", "xiaohongshu"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
