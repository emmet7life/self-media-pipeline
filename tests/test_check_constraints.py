from __future__ import annotations

"""

test_check_constraints.py —— 锁住 check_constraints.py 的硬约束检查行为

P0-B 复发点: 之前 reviewer subagent 找不到 skills/platform-xiaohongshu/ 报 block.
            本测试文件防止硬约束检查行为回归.

P1 锁点: 合规 draft 必须 pass=true; 不合规 draft 必须 block > 0.

运行：
    cd ~/self-media-pipeline
    python3 tests/test_check_constraints.py
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
WECHAT_CHECK = PLUGIN_ROOT / "skills" / "platform-wechat" / "tools" / "check_constraints.py"
XHS_CHECK = PLUGIN_ROOT / "skills" / "platform-xiaohongshu" / "tools" / "check_constraints.py"


def run_check(check_script: Path, draft: Path, constraints: Path | None = None, out: Path | None = None):
    cmd = [sys.executable, str(check_script), str(draft)]
    if constraints:
        cmd += ["--constraints", str(constraints)]
    if out:
        cmd += ["--out", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return r.returncode, r.stdout, r.stderr


def make_draft(tmp, body, title="test", word_count=None, **extra):
    d = {
        "title": title,
        "body_markdown": body,
        "images": [],
        "metadata": {
            "word_count": word_count if word_count is not None else len(body),
            "reading_time_min": 1,
        },
    }
    d.update(extra)
    p = tmp / "draft.json"
    p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return p


class TestWechatConstraints(unittest.TestCase):
    """公众号硬约束检查."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_compliant_draft_passes(self):
        """合规 draft: 标题 8-30, 正文 600-5000, 必须 pass."""
        body = "这是正文。" * 150  # 750 chars, 在 [600, 5000] 范围内
        draft = make_draft(self.tmp_dir, body=body, title="测试标题 8-30 个字符",
                           word_count=750)
        rc, stdout, stderr = run_check(WECHAT_CHECK, draft)
        self.assertEqual(rc, 0, f"compliant draft should pass, got: {stderr}")
        report = json.loads(stdout)
        self.assertTrue(report["pass"], f"compliant draft pass should be true, got: {report}")
        self.assertEqual(report["summary"]["block"], 0)

    def test_body_too_short_blocked(self):
        """正文 < 600 chars → block."""
        body = "短" * 50
        draft = make_draft(self.tmp_dir, body=body, title="OK 标题", word_count=50)
        rc, stdout, _ = run_check(WECHAT_CHECK, draft)
        report = json.loads(stdout)
        # exit code 1 表示 block 出现
        self.assertNotEqual(rc, 0, "exit code must be non-zero on block")
        self.assertFalse(report["pass"], "short body should fail")
        self.assertGreater(report["summary"]["block"], 0)
        # 至少一个 issue 提到 body/字数
        issue_msgs = " ".join(i.get("message", "") for i in report["issues"]).lower()
        self.assertTrue(
            "body" in issue_msgs or "字符" in issue_msgs or "chars" in issue_msgs or "min" in issue_msgs,
            f"issues should mention body length: {report['issues']}"
        )

    def test_body_too_long_blocked(self):
        """正文 > 5000 chars → block."""
        body = "长" * 5500
        draft = make_draft(self.tmp_dir, body=body, title="OK 标题", word_count=5500)
        rc, stdout, _ = run_check(WECHAT_CHECK, draft)
        report = json.loads(stdout)
        self.assertFalse(report["pass"])
        self.assertGreater(report["summary"]["block"], 0)

    def test_title_too_short_blocked(self):
        """标题 < 8 chars → block."""
        body = "这是正文。" * 100
        draft = make_draft(self.tmp_dir, body=body, title="短标", word_count=500)
        rc, stdout, _ = run_check(WECHAT_CHECK, draft)
        report = json.loads(stdout)
        self.assertFalse(report["pass"])
        self.assertGreater(report["summary"]["block"], 0)

    def test_forbidden_tag_in_html_blocked(self):
        """inline_html 含 <script> → block (P0-B 公众号清洗约束)."""
        body = "这是正文。" * 100
        draft = make_draft(self.tmp_dir, body=body, title="OK 标题 8-30",
                           word_count=500, inline_html="<p>body</p><script>alert(1)</script>")
        rc, stdout, _ = run_check(WECHAT_CHECK, draft)
        report = json.loads(stdout)
        # 应该 block <script>
        issue_constraints = [i.get("constraint", "") for i in report["issues"]]
        # 至少一个 block-level issue 提到 script 或 forbidden
        block_issues = [i for i in report["issues"] if i.get("severity") == "block"]
        self.assertGreater(len(block_issues), 0, f"expected block on script, got: {report}")


class TestXiaohongshuConstraints(unittest.TestCase):
    """小红书硬约束检查."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_compliant_draft_passes(self):
        """合规小红书 draft: 标题 6-20 含 emoji, 正文 100-1000, 3+ 标签, 1-9 图 → pass."""
        draft = PLUGIN_ROOT / "examples" / "hello-world" / "templates" / "draft-xiaohongshu.json"
        if not draft.exists():
            self.skipTest("template draft-xiaohongshu.json not found")
        rc, stdout, _ = run_check(XHS_CHECK, draft)
        report = json.loads(stdout)
        self.assertTrue(report["pass"], f"compliant template should pass: {report}")
        self.assertEqual(report["summary"]["block"], 0)

    def test_title_without_emoji_blocked(self):
        """小红书标题必须含 emoji, 否则 block."""
        body = "姐妹们分享内容" * 30
        # 写 4 个 # 标签让标签数过
        body_with_tags = body + "\n\n#AI #AI工具 #编程 #学习"
        draft = make_draft(self.tmp_dir, body=body_with_tags, title="无 emoji 标题",
                           word_count=len(body_with_tags), images=[{"slot": "cover", "width_px": 1080, "height_px": 1440, "prompt": "x"}])
        rc, stdout, _ = run_check(XHS_CHECK, draft)
        report = json.loads(stdout)
        self.assertFalse(report["pass"], "no-emoji title should fail")
        self.assertGreater(report["summary"]["block"], 0)
        # 至少一个 issue 提到 emoji
        issue_msgs = " ".join(i.get("message", "") for i in report["issues"])
        self.assertIn("emoji", issue_msgs.lower(), f"expected emoji issue: {report['issues']}")

    def test_too_few_tags_blocked(self):
        """小红书 < 3 标签 → block."""
        body = "姐妹们分享" * 30 + "\n\n#AI"
        draft = make_draft(self.tmp_dir, body=body, title="带 emoji🌟",
                           word_count=len(body), images=[{"slot": "cover", "width_px": 1080, "height_px": 1440, "prompt": "x"}])
        rc, stdout, _ = run_check(XHS_CHECK, draft)
        report = json.loads(stdout)
        self.assertFalse(report["pass"])
        self.assertGreater(report["summary"]["block"], 0)

    def test_body_too_short_blocked(self):
        """正文 < 100 chars → block."""
        body = "短"
        draft = make_draft(self.tmp_dir, body=body, title="emoji🌟",
                           word_count=1, images=[{"slot": "cover", "width_px": 1080, "height_px": 1440, "prompt": "x"}])
        rc, stdout, _ = run_check(XHS_CHECK, draft)
        report = json.loads(stdout)
        self.assertFalse(report["pass"])


class TestCheckConstraintsReportSchema(unittest.TestCase):
    """report schema 契约: 任何平台 check_constraints.py 都必须输出该 schema."""

    REQUIRED_KEYS = {"pass", "issues", "summary"}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_wechat_report_schema(self):
        """wechat 报告必须有 pass/issues/summary 三字段."""
        body = "正常正文" * 100
        draft = make_draft(self.tmp_dir, body=body, title="OK 标题 8-30",
                           word_count=500)
        rc, stdout, _ = run_check(WECHAT_CHECK, draft)
        report = json.loads(stdout)
        self.assertTrue(self.REQUIRED_KEYS.issubset(report.keys()))
        # summary 必须有 block/warn/info 三个子键
        self.assertIn("block", report["summary"])
        self.assertIn("warn", report["summary"])
        self.assertIn("info", report["summary"])

    def test_xhs_report_schema(self):
        """xhs 报告 schema 同 wechat."""
        body = "正文" * 50 + "\n\n#AI #AI工具 #编程"
        draft = make_draft(self.tmp_dir, body=body, title="emoji🌟",
                           word_count=len(body),
                           images=[{"slot": "cover", "width_px": 1080, "height_px": 1440, "prompt": "x"}])
        rc, stdout, _ = run_check(XHS_CHECK, draft)
        report = json.loads(stdout)
        self.assertTrue(self.REQUIRED_KEYS.issubset(report.keys()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
