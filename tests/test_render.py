"""
test_render.py —— 锁住 render.py 的 CLI 契约

P0-A 复发点：之前 Claude Code 把 draft JSON 当 positional input 传给 render.py，
            整个 JSON 被当 markdown 渲染，产物是 raw JSON 字符的 HTML。
            本测试文件防止这个 bug 复发。

运行：
    cd ~/self-media-pipeline
    python3 tests/test_render.py

或：
    python3 -m unittest tests.test_render -v
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
RENDER_PY = PLUGIN_ROOT / "skills" / "render-html" / "tools" / "render.py"


def run_render(args, stdin_text=None):
    """Run render.py with given args, return (returncode, stdout, stderr)."""
    cmd = [sys.executable, str(RENDER_PY), *args]
    r = subprocess.run(cmd, input=stdin_text, capture_output=True, text=True, timeout=30)
    return r.returncode, r.stdout, r.stderr


def make_draft(tmp, body="# Title\n\nHello world.", title="test title", extra=None):
    """Helper: write a draft contract JSON to tmp, return path."""
    draft = {
        "title": title,
        "body_markdown": body,
        "images": [],
        "metadata": {"word_count": 3, "reading_time_min": 1},
    }
    if extra:
        draft.update(extra)
    p = tmp / "draft.json"
    p.write_text(json.dumps(draft, ensure_ascii=False), encoding="utf-8")
    return p


class TestRenderFromDraft(unittest.TestCase):
    """Tests for --from-draft flag (P0-A 修复点)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_from_draft_extracts_body_markdown(self):
        """P0-A 锁点: --from-draft 必须抽 body_markdown，不能渲染 raw JSON."""
        draft = make_draft(
            self.tmp_dir,
            body="这是正文第一段。\n\n这是第二段。",
            title="测试标题",
        )
        out_html = self.tmp_dir / "out.html"
        rc, stdout, stderr = run_render(["--from-draft", str(draft), "-o", str(out_html)])

        self.assertEqual(rc, 0, f"render failed: {stderr}")
        self.assertTrue(out_html.exists(), "output HTML not written")
        html = out_html.read_text(encoding="utf-8")

        # 关键断言 1: 正文 body_markdown 内容出现在 HTML
        self.assertIn("这是正文第一段", html, "body_markdown not extracted into HTML")
        # 关键断言 2: raw JSON 字符 ({"title"...) 不应该出现在 HTML body
        self.assertNotIn('"title":', html, "raw JSON leaked into HTML body — P0-A regressed!")
        self.assertNotIn('"body_markdown":', html, "raw JSON leaked into HTML body — P0-A regressed!")
        # 关键断言 3: title 在 <title> 标签里
        self.assertIn("<title>测试标题</title>", html, "title not extracted into <title> tag")

    def test_from_draft_with_unicode_title(self):
        """Title 含 emoji / 中文时仍正确传递."""
        draft = make_draft(
            self.tmp_dir,
            body="body",
            title="AI Agent 入门🌟 3 步上手！",
        )
        out_html = self.tmp_dir / "out.html"
        rc, _, _ = run_render(["--from-draft", str(draft), "-o", str(out_html)])
        self.assertEqual(rc, 0)
        html = out_html.read_text(encoding="utf-8")
        self.assertIn("AI Agent 入门🌟 3 步上手！", html)

    def test_from_draft_missing_body_field_fails(self):
        """Draft JSON 缺 body_markdown 字段时必须失败（不静默渲染空 HTML）."""
        draft_path = self.tmp_dir / "bad.json"
        draft_path.write_text(json.dumps({"title": "no body"}), encoding="utf-8")
        rc, stdout, stderr = run_render(["--from-draft", str(draft_path)])

        # 必须失败
        self.assertNotEqual(rc, 0, "render should fail when body_markdown missing")
        # 错误信息要 hint 到字段名
        self.assertIn("body_markdown", (stderr + stdout).lower())

    def test_from_draft_malformed_json_fails(self):
        """Draft 文件不是合法 JSON 时必须失败."""
        bad = self.tmp_dir / "bad.json"
        bad.write_text("not json {", encoding="utf-8")
        rc, _, stderr = run_render(["--from-draft", str(bad)])
        self.assertNotEqual(rc, 0, "render should fail on malformed JSON")

    def test_from_draft_nonexistent_file_fails(self):
        """Draft 路径不存在时必须失败."""
        rc, _, stderr = run_render(["--from-draft", "/nonexistent/path.json"])
        self.assertNotEqual(rc, 0, "render should fail on missing file")


class TestRenderPositionalMarkdown(unittest.TestCase):
    """Tests for positional markdown file input (legacy path)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_markdown_file_renders_correctly(self):
        """纯 markdown 文件 → 正常渲染."""
        md = self.tmp_dir / "a.md"
        md.write_text("# Hello\n\nworld", encoding="utf-8")
        out_html = self.tmp_dir / "out.html"
        rc, _, _ = run_render([str(md), "-o", str(out_html)])
        self.assertEqual(rc, 0)
        html = out_html.read_text(encoding="utf-8")
        self.assertIn("<h1", html)
        self.assertIn("Hello", html)
        self.assertIn("world", html)

    def test_stdin_renders_correctly(self):
        """stdin 输入 markdown → 正常渲染."""
        out_html = self.tmp_dir / "out.html"
        rc, _, _ = run_render(["-o", str(out_html)], stdin_text="# stdin\n\nbody")
        self.assertEqual(rc, 0)
        html = out_html.read_text(encoding="utf-8")
        self.assertIn("stdin", html)
        self.assertIn("body", html)

    def test_title_flag_sets_title_tag(self):
        """--title 参数设置 <title> 标签."""
        md = self.tmp_dir / "a.md"
        md.write_text("body", encoding="utf-8")
        out_html = self.tmp_dir / "out.html"
        rc, _, _ = run_render([str(md), "-o", str(out_html), "--title", "My Title"])
        self.assertEqual(rc, 0)
        html = out_html.read_text(encoding="utf-8")
        self.assertIn("<title>My Title</title>", html)


class TestRenderCLIBoundary(unittest.TestCase):
    """P0-A 锁点: 错用错误信息必须清晰. 防止 'silent garbage output' 模式复发."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_draft_json_as_positional_must_not_silently_garbage_render(self):
        """
        P0-A 复发 guard: 把 draft JSON 当 positional input 传给 render.py.
        期望: 要么 exit code != 0 (error), 要么产物不包含 raw JSON 字段.
        这是允许退而求其次的合约 - 只要不是 'silent garbage' 就 OK.
        """
        draft = make_draft(self.tmp_dir, body="GOOD CONTENT", title="GOOD TITLE")
        out_html = self.tmp_dir / "out.html"
        # 故意把 draft JSON 当 positional input 传（错误用法）
        rc, _, stderr = run_render([str(draft), "-o", str(out_html)])

        if rc == 0:
            # 如果 exit 0，那产物必须是 GOOD 内容（不能是 raw JSON）
            html = out_html.read_text(encoding="utf-8")
            self.assertIn("GOOD CONTENT", html, "Positional mode: body_markdown must be rendered if it is in the file")
            # raw JSON 字符不应该在 body 里出现
            self.assertNotIn('"title":', html, "P0-A REGRESSION: raw JSON leaked into output")
        else:
            # 如果 exit 非零，那 stderr 必须有清晰的错误信息
            self.assertTrue(len(stderr) > 0, "On error, stderr must have a message")

    def test_from_draft_and_positional_are_mutually_exclusive(self):
        """--from-draft 和 positional input 不能同时用."""
        md = self.tmp_dir / "a.md"
        md.write_text("body", encoding="utf-8")
        draft = make_draft(self.tmp_dir, body="body2")
        rc, _, _ = run_render([str(md), "--from-draft", str(draft)])
        self.assertNotEqual(rc, 0, "render must reject --from-draft + positional together")


class TestRenderStyleInline(unittest.TestCase):
    """锁住 inline-CSS 行为（公众号可粘贴性的关键）."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_h1_has_inline_font_size(self):
        """H1 必须有 inline style (font-size, font-weight)."""
        draft = make_draft(self.tmp_dir, body="# 标题\n\n正文", title="t")
        out_html = self.tmp_dir / "out.html"
        rc, _, _ = run_render(["--from-draft", str(draft), "-o", str(out_html)])
        self.assertEqual(rc, 0)
        html = out_html.read_text(encoding="utf-8")
        self.assertIn('font-size: 1.875em', html, "H1 missing inline font-size")
        self.assertIn("font-weight: 700", html, "H1 missing inline font-weight")

    def test_class_attributes_removed(self):
        """公众号清洗: class 属性必须被剥除 (公众号编辑器会丢 class 样式)."""
        draft = make_draft(self.tmp_dir, body="正文", title="t")
        out_html = self.tmp_dir / "out.html"
        rc, _, _ = run_render(["--from-draft", str(draft), "-o", str(out_html)])
        self.assertEqual(rc, 0)
        html = out_html.read_text(encoding="utf-8")
        # markdown-it 给 <h1> 不会加 class, 但 <table class="..."> 会; 这里简单断言 <article> 元素不带 class
        self.assertNotIn('class="smp-article"', html, "class attribute not stripped")


if __name__ == "__main__":
    unittest.main(verbosity=2)
