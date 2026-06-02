"""
test_template_library.py —— 锁住模板库最小契约。
"""
import subprocess
import sys
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
LIST_TEMPLATES = PLUGIN_ROOT / "tools" / "list-templates"


class TestTemplateLibrary(unittest.TestCase):
    def test_builtin_templates_have_skill_and_example(self):
        for template_id in ["wechat-magazine-editorial", "xhs-pastel-card-deck"]:
            root = PLUGIN_ROOT / "templates" / template_id
            self.assertTrue((root / "SKILL.md").exists(), f"{template_id} missing SKILL.md")
            self.assertTrue((root / "example.html").exists(), f"{template_id} missing example.html")

    def test_list_templates_cli(self):
        result = subprocess.run(
            [sys.executable, str(LIST_TEMPLATES)],
            cwd=PLUGIN_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("wechat-magazine-editorial", result.stdout)
        self.assertIn("xhs-pastel-card-deck", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
