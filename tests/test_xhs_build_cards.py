"""
test_xhs_build_cards.py —— 锁住小红书逐卡片 HTML 生成契约。
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
BUILD_CARDS = PLUGIN_ROOT / "skills" / "platform-xiaohongshu" / "tools" / "build_cards.py"
SAMPLE_DRAFT = PLUGIN_ROOT / "examples" / "hello-world" / "templates" / "draft-xiaohongshu.json"


class TestXhsBuildCards(unittest.TestCase):
    def test_builds_independent_html_cards(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "cards"
            result = subprocess.run(
                [
                    sys.executable,
                    str(BUILD_CARDS),
                    "--draft",
                    str(SAMPLE_DRAFT),
                    "--output-dir",
                    str(out),
                    "--count",
                    "9",
                ],
                cwd=PLUGIN_ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            cards = sorted(out.glob("[0-9][0-9].html"))
            self.assertEqual(len(cards), 9)
            self.assertTrue((out / "manifest.json").exists())

            manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["size"], {"width_px": 1080, "height_px": 1440})

            first = cards[0].read_text(encoding="utf-8")
            self.assertIn("width: 1080px", first)
            self.assertIn("height: 1440px", first)
            self.assertNotIn("slice_grid", first)


if __name__ == "__main__":
    unittest.main(verbosity=2)
