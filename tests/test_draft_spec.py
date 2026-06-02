from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
DRAFT_SPEC = PLUGIN_ROOT / "tools" / "draft-spec"


class TestDraftSpecTemplateSelection(unittest.TestCase):
    def run_draft_spec(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(DRAFT_SPEC), *args],
            cwd=PLUGIN_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def test_default_templates_are_written_for_multiple_platforms(self):
        result = self.run_draft_spec(
            "--topic", "AI Agent 入门",
            "--platforms", "wechat,xiaohongshu",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        spec = json.loads(result.stdout)
        self.assertEqual(spec["target_platforms"], ["wechat", "xiaohongshu"])
        self.assertEqual(spec["template_selection"]["wechat"], "wechat-magazine-editorial")
        self.assertEqual(spec["template_selection"]["xiaohongshu"], "xhs-pastel-card-deck")

    def test_explicit_single_platform_template(self):
        result = self.run_draft_spec(
            "--topic", "AI Agent 入门",
            "--platforms", "wechat",
            "--templates", "wechat=wechat-magazine-editorial",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        spec = json.loads(result.stdout)
        self.assertEqual(spec["target_platforms"], ["wechat"])
        self.assertEqual(spec["template_selection"], {"wechat": "wechat-magazine-editorial"})

    def test_rejects_unknown_platform(self):
        result = self.run_draft_spec(
            "--topic", "AI Agent 入门",
            "--platforms", "zhihu",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown or inactive platform", result.stderr)
        self.assertIn("planned but not selectable", result.stderr)

    def test_rejects_template_for_wrong_platform(self):
        result = self.run_draft_spec(
            "--topic", "AI Agent 入门",
            "--platforms", "wechat",
            "--templates", "wechat=xhs-pastel-card-deck",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("belongs to platform", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
