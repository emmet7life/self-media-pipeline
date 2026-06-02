"""
test_template_library.py —— 锁住模板库最小契约。
"""
import subprocess
import sys
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT / "tools"))

from _catalog import list_templates, validate_catalog  # noqa: E402

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

    def test_list_templates_json_can_filter_by_platform(self):
        result = subprocess.run(
            [sys.executable, str(LIST_TEMPLATES), "--platform", "wechat", "--json"],
            cwd=PLUGIN_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"id": "wechat-magazine-editorial"', result.stdout)
        self.assertNotIn('"id": "xhs-pastel-card-deck"', result.stdout)

    def test_catalog_validation_passes(self):
        self.assertEqual(validate_catalog(), [])

    def test_builtin_templates_have_required_frontmatter(self):
        templates = {template["id"]: template for template in list_templates()}
        wechat = templates["wechat-magazine-editorial"]
        xhs = templates["xhs-pastel-card-deck"]

        self.assertEqual(wechat["platform"], "wechat")
        self.assertTrue(wechat["default"])
        self.assertEqual(wechat["status"], "active")
        self.assertEqual(wechat["content_type"], "longform")

        self.assertEqual(xhs["platform"], "xiaohongshu")
        self.assertTrue(xhs["default"])
        self.assertEqual(xhs["status"], "active")
        self.assertEqual(xhs["output_kind"], "independent_card_html")


if __name__ == "__main__":
    unittest.main(verbosity=2)
