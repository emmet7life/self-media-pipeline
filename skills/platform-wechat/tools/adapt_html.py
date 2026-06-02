#!/usr/bin/env python3
"""
adapt_html.py —— 微信公众号编辑器适配器

输入: HTML 字符串（或文件路径）
输出: 适配后的 HTML（可粘贴到公众号后台）

做的事:
1. 移除 <script>、外部 <link rel=stylesheet>、外部字体引用
2. 替换 <img data-wx-src="..."> 占位为 <img src="...">
3. 包裹一层 <section data-tool="html-anything"> 让微信信任
4. 强制所有 <table> 添加 border 属性（微信会剥 CSS border）

输入来源：一般是 skills/render-html/tools/render.py 的输出
"""
import argparse
import sys
from pathlib import Path

from bs4 import BeautifulSoup


def adapt_for_wechat(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    # 1. 移除 script
    for tag in soup.find_all("script"):
        tag.decompose()

    # 2. 移除外部 stylesheet 链接
    for link in soup.find_all("link", attrs={"rel": "stylesheet"}):
        link.decompose()

    # 3. 移除 @import / @font-face（已经 inline 完就不会有，但防御性删除）
    for style in soup.find_all("style"):
        if style.string and ("@import" in style.string or "@font-face" in style.string):
            style.decompose()

    # 4. <img data-wx-src="..." data-slot="..."> → <img src="...">
    for img in soup.find_all("img"):
        wx_src = img.get("data-wx-src")
        slot = img.get("data-slot")
        if wx_src:
            img["src"] = wx_src
        if slot:
            img["data-slot"] = slot  # 保留标记，供后续处理

    # 5. 表格加 border 属性（微信会剥 CSS border）
    for table in soup.find_all("table"):
        table["border"] = "1"
        table["cellspacing"] = "0"
        table["cellpadding"] = "8"

    # 6. 包一层 <section data-tool="html-anything"> 让微信识别为可信内容块
    body = soup.find("body")
    if body:
        wrapper = soup.new_tag("section", attrs={"data-tool": "html-anything"})
        # 把 body 的内容搬到 wrapper
        for child in list(body.children):
            wrapper.append(child.extract() if hasattr(child, 'extract') else child)
        body.append(wrapper)

    return str(soup)


def main() -> None:
    ap = argparse.ArgumentParser(description="Adapt HTML for WeChat editor")
    ap.add_argument("input", nargs="?", help="input HTML file (default stdin)")
    ap.add_argument("-o", "--output", help="output HTML file (default stdout)")
    ap.add_argument("--validate", action="store_true", help="run basic validation (forbidden tags etc.)")
    args = ap.parse_args()

    if args.input:
        html = Path(args.input).read_text(encoding="utf-8")
    else:
        html = sys.stdin.read()

    adapted = adapt_for_wechat(html)

    if args.validate:
        # 简单校验：确认 <script> / <link rel=stylesheet> 已清干净
        if "<script" in adapted.lower():
            print("WARN: <script> still present", file=sys.stderr)
        if "<link" in adapted.lower() and 'rel="stylesheet"' in adapted.lower():
            print("WARN: <link rel=stylesheet> still present", file=sys.stderr)

    if args.output:
        Path(args.output).write_text(adapted, encoding="utf-8")
        print(f"wrote {args.output} ({len(adapted)} bytes)", file=sys.stderr)
    else:
        print(adapted)


if __name__ == "__main__":
    main()
