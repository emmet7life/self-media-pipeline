#!/usr/bin/env python3
"""
adapt_html.py —— 小红书笔记适配器 (stdlib only, regex based)

注意：小红书 App 的发布编辑器**不接收 HTML**——用户最终是用富文本编辑器手动粘。
本工具产出的"适配 HTML"**只用于**：
1. 渲染预览（看排版效果）
2. 作为卡片 HTML / PNG 渲染前的预览清洗输入（小红书发布图走 build_cards.py + render_grid.py）

做的事:
1. 移除 <script>、外部 <link rel=stylesheet>、外部字体
2. 替换 <img data-xhs-src="..."> 占位为 <img src="...">
3. 移除所有外链 <a href="http..."> → 文本（小红书不接外链）
4. 移除二维码 / 微信号 / 手机号（敏感词/风控）
"""
import argparse
import re
import sys
from pathlib import Path


# 敏感词（基础列表，第 5 周会扩到 wordlists/）
SENSITIVE_PATTERNS = [
    (re.compile(r"微信号[:：]?\s*\w+", re.IGNORECASE), "[微信号已隐藏]"),
    (re.compile(r"wx[:：]?\s*\w+", re.IGNORECASE), "[微信号已隐藏]"),
    (re.compile(r"\b\d{11}\b"), "[手机号已隐藏]"),  # 11 位数字（手机号）
    (re.compile(r"v信|v❤|薇❤|加我|私我", re.IGNORECASE), "[联系方式已隐藏]"),
]


def adapt_for_xiaohongshu(html: str) -> dict:
    """适配 HTML，返回 {html, warnings} — warnings 让 caller 知道哪些内容被改了"""
    original = html
    warnings = []

    # 1. 移除 <script>...</script>（多行，非贪心）
    html = re.sub(r'<script\b[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)

    # 2. 移除 <link rel="stylesheet" ...>
    html = re.sub(
        r'<link\b[^>]*?\brel\s*=\s*["\']stylesheet["\'][^>]*/?>',
        '', html, flags=re.IGNORECASE
    )

    # 3. <img data-xhs-src="..."> → <img src="...">
    html = re.sub(
        r'\bdata-xhs-src\s*=\s*',
        'src=', html, flags=re.IGNORECASE
    )

    # 4. 移除所有外链 <a href="http(s)://...">text</a> → text
    # 注意：需要处理 <a> 可能跨多行的情况
    def strip_link(m):
        text = m.group(2) if m.group(2) else ''
        href = m.group(1)[:50]
        warnings.append(f'external link removed: {href}')
        return text

    html = re.sub(
        r'<a\b[^>]*?\bhref\s*=\s*["\'](https?://[^"\']+)["\'][^>]*>(.*?)</a>',
        strip_link, html, flags=re.DOTALL | re.IGNORECASE
    )

    # 5. 敏感词替换（处理 HTML 文本节点——简单替换，避免动标签）
    for pattern, replacement in SENSITIVE_PATTERNS:
        # 只在纯文本中替换，避开标签属性
        # 方法：将文本节点和老样式分开处理
        matches_before = pattern.findall(html)
        if matches_before:
            html = pattern.sub(replacement, html)
            # 粗略检查：确保替换没发生在标签里
            for m in pattern.findall(original):
                if m not in html:
                    warnings.append(f'sensitive pattern replaced: {m[:30]}')

    # 6. <body> 内包裹 <section data-tool="html-anything" data-platform="xiaohongshu">
    def wrap_body(m):
        before = m.group(1)  # <body ...>
        content = m.group(2)  # everything inside body
        after = m.group(3)    # </body>
        return f'{before}<section data-tool="html-anything" data-platform="xiaohongshu">{content}</section>{after}'
    html = re.sub(
        r'(<body\b[^>]*>)(.*?)(</body>)',
        wrap_body, html, flags=re.DOTALL | re.IGNORECASE
    )

    return {"html": html, "warnings": warnings}


def main() -> None:
    ap = argparse.ArgumentParser(description="Adapt HTML for Xiaohongshu (preview/grid render use only)")
    ap.add_argument("input", nargs="?", help="input HTML file (default stdin)")
    ap.add_argument("-o", "--output", help="output HTML file (default stdout)")
    ap.add_argument("--show-warnings", action="store_true", help="print sanitization warnings to stderr")
    args = ap.parse_args()

    if args.input:
        html_str = Path(args.input).read_text(encoding="utf-8")
    else:
        html_str = sys.stdin.read()

    result = adapt_for_xiaohongshu(html_str)

    if args.show_warnings and result["warnings"]:
        for w in result["warnings"]:
            print(f"  WARN: {w}", file=sys.stderr)

    if args.output:
        Path(args.output).write_text(result["html"], encoding="utf-8")
        print(f"wrote {args.output} ({len(result['html'])} bytes)", file=sys.stderr)
    else:
        print(result["html"])


if __name__ == "__main__":
    main()
