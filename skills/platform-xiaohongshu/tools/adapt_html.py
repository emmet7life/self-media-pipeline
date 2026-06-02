#!/usr/bin/env python3
"""
adapt_html.py —— 小红书笔记适配器

注意：小红书 App 的发布编辑器**不接收 HTML**——用户最终是用富文本编辑器手动粘。
本工具产出的"适配 HTML"**只用于**：
1. 渲染预览（看排版效果）
2. 作为卡片 HTML / PNG 渲染前的预览清洗输入（小红书发布图走 build_cards.py + render_grid.py）

做的事:
1. 移除 <script>、外部 <link rel=stylesheet>、外部字体
2. 替换 <img data-xhs-src="..."> 占位为 <img src="...">
3. 移除所有外链 <a href="http..."> → 文本（小红书不接外链）
4. 移除二维码 / 微信号 / 手机号（敏感词/风控）

输入来源：skills/render-html/tools/render.py 的输出
"""
import argparse
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup


# 敏感词（基础列表，第 5 周会扩到 wordlists/）
SENSITIVE_PATTERNS = [
    (re.compile(r"微信号[:：]?\s*\w+", re.IGNORECASE), "[微信号已隐藏]"),
    (re.compile(r"wx[:：]?\s*\w+", re.IGNORECASE), "[微信号已隐藏]"),
    (re.compile(r"\d{11}"), "[手机号已隐藏]"),  # 11 位数字（手机号）
    (re.compile(r"v信|v❤|薇❤|加我|私我", re.IGNORECASE), "[联系方式已隐藏]"),
]


def adapt_for_xiaohongshu(html: str) -> dict:
    """适配 HTML，返回 {html, warnings} — warnings 让 caller 知道哪些内容被改了"""
    soup = BeautifulSoup(html, "html.parser")
    warnings = []

    # 1. 移除 script
    for tag in soup.find_all("script"):
        tag.decompose()

    # 2. 移除外部 stylesheet 链接
    for link in soup.find_all("link", attrs={"rel": "stylesheet"}):
        link.decompose()

    # 3. <img data-xhs-src="..."> → <img src="...">
    for img in soup.find_all("img"):
        xhs_src = img.get("data-xhs-src")
        if xhs_src:
            img["src"] = xhs_src
        slot = img.get("data-slot")
        if slot:
            img["data-slot"] = slot

    # 4. 移除所有外链（http://, https://）→ 转成纯文本
    for a in soup.find_all("a"):
        href = a.get("href", "") or ""
        if not isinstance(href, str):
            href = " ".join(href) if href else ""
        if href.startswith("http://") or href.startswith("https://"):
            warnings.append(f"external link removed: {href[:50]}")
            a.replace_with(a.get_text())  # 替换为纯文本

    # 5. 敏感词替换（处理 text 节点）
    for pattern, replacement in SENSITIVE_PATTERNS:
        for element in soup.find_all(string=pattern):
            original = str(element)
            new_text = pattern.sub(replacement, original)
            if new_text != original:
                warnings.append(f"sensitive pattern replaced: {original[:30]}")
                element.replace_with(BeautifulSoup(new_text, "html.parser"))

    # 6. 包裹一层
    body = soup.find("body")
    if body:
        wrapper = soup.new_tag("section", attrs={"data-tool": "html-anything", "data-platform": "xiaohongshu"})
        for child in list(body.children):
            wrapper.append(child.extract() if hasattr(child, 'extract') else child)
        body.append(wrapper)

    return {"html": str(soup), "warnings": warnings}


def main() -> None:
    ap = argparse.ArgumentParser(description="Adapt HTML for Xiaohongshu (preview/grid render use only)")
    ap.add_argument("input", nargs="?", help="input HTML file (default stdin)")
    ap.add_argument("-o", "--output", help="output HTML file (default stdout)")
    ap.add_argument("--show-warnings", action="store_true", help="print sanitization warnings to stderr")
    args = ap.parse_args()

    if args.input:
        html = Path(args.input).read_text(encoding="utf-8")
    else:
        html = sys.stdin.read()

    result = adapt_for_xiaohongshu(html)

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
