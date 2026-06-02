#!/usr/bin/env python3
"""
adapt_html.py —— 微信公众号编辑器适配器 (stdlib only, regex based)

Simple regex transformations for WeChat editor compatibility.
Much simpler and more robust than a full HTML parser for these specific ops.
"""
import argparse
import re
import sys
from pathlib import Path


def adapt_for_wechat(html: str) -> str:
    """Adapt HTML for WeChat editor using regex transformations."""

    # 1. Remove <script>...</script> (non-greedy, multiline)
    html = re.sub(r'<script\b[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)

    # 2. Remove <link rel="stylesheet" ...>
    html = re.sub(
        r'<link\b[^>]*?\brel\s*=\s*["\']stylesheet["\'][^>]*/?>',
        '', html, flags=re.IGNORECASE
    )

    # 3. Remove <style>...</style> (already inlined, so safe to strip)
    html = re.sub(r'<style\b[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)

    # 4. <img data-wx-src="..."> -> <img src="...">
    def fix_img(m):
        before = m.group(1)
        attrs = m.group(2)
        after = m.group(3) if m.group(3) else ''
        # Rewrite data-wx-src to src
        attrs = re.sub(r'\bdata-wx-src\s*=', 'src=', attrs)
        return f'<img{before}{attrs}{after}'
    html = re.sub(
        r'<img(\s+)((?:[^>]*?data-wx-src[^>]*?)?)(\s*/?\s*>)?',
        fix_img, html, flags=re.IGNORECASE
    )

    # 5. <body> content wrapper: wrap entire body content in <section data-tool="html-anything">
    def wrap_body(m):
        before = m.group(1)  # <body ...>
        content = m.group(2)  # everything inside body
        after = m.group(3)    # </body>
        return f'{before}<section data-tool="html-anything">{content}</section>{after}'
    html = re.sub(
        r'(<body\b[^>]*>)(.*?)(</body>)',
        wrap_body, html, flags=re.DOTALL | re.IGNORECASE
    )

    # 6. Tables: add border/cellspacing/cellpadding if missing
    def fix_table(m):
        tag = m.group(1)  # <table ...> or <table>
        if 'border' not in tag:
            tag = tag.rstrip('>') + ' border="1" cellspacing="0" cellpadding="8">'
        return tag
    html = re.sub(r'<table\b([^>]*)>', fix_table, html, flags=re.IGNORECASE)

    return html


def main() -> None:
    ap = argparse.ArgumentParser(description="Adapt HTML for WeChat editor")
    ap.add_argument("input", nargs="?", help="input HTML file (default stdin)")
    ap.add_argument("-o", "--output", help="output HTML file (default stdout)")
    ap.add_argument("--validate", action="store_true", help="run basic validation")
    args = ap.parse_args()

    if args.input:
        html_str = Path(args.input).read_text(encoding="utf-8")
    else:
        html_str = sys.stdin.read()

    adapted = adapt_for_wechat(html_str)

    if args.validate:
        cleaned = adapted.lower()
        if re.search(r'<script[>\s]', cleaned):
            print("WARN: <script> still present", file=sys.stderr)
        if re.search(r'<link\b[^>]*rel\s*=\s*["\']stylesheet["\']', cleaned):
            print("WARN: <link rel=stylesheet> still present", file=sys.stderr)

    if args.output:
        Path(args.output).write_text(adapted, encoding="utf-8")
        print(f"wrote {args.output} ({len(adapted)} bytes)", file=sys.stderr)
    else:
        print(adapted)


if __name__ == "__main__":
    main()
