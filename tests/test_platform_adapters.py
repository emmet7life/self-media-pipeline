from __future__ import annotations

import sys
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT / "skills" / "platform-wechat" / "tools"))

from adapt_html import adapt_for_wechat  # noqa: E402


class TestWechatAdapter(unittest.TestCase):
    def test_table_tag_is_preserved_when_adding_wechat_attrs(self):
        html = """<!doctype html>
<html><body><article>
<table style="border-collapse: collapse"><tr><td>LangChain</td></tr></table>
</article></body></html>"""

        adapted = adapt_for_wechat(html)

        self.assertIn('<table style="border-collapse: collapse" border="1"', adapted)
        self.assertIn("<td>LangChain</td>", adapted)
        self.assertNotIn('\n style="border-collapse: collapse"', adapted)
        self.assertIn('<section data-tool="html-anything">', adapted)

    def test_script_and_stylesheet_links_are_removed(self):
        html = """<html><head><link rel="stylesheet" href="x.css"></head>
<body><script>alert(1)</script><p>ok</p></body></html>"""

        adapted = adapt_for_wechat(html)

        self.assertNotIn("<script", adapted.lower())
        self.assertNotIn("stylesheet", adapted.lower())
        self.assertIn("<p>ok</p>", adapted)


if __name__ == "__main__":
    unittest.main(verbosity=2)
