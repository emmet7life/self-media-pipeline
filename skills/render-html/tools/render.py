#!/usr/bin/env python3
"""
render.py —— 把 markdown 渲染成"inline HTML"（公众号可粘贴版）

输入 (三种方式，按优先级):
1. --from-draft <draft.json>  ← 推荐：draft 契约 JSON（含 body_markdown + title）
2. input 位置参数            ← 纯 markdown 文件路径
3. stdin                     ← 纯 markdown 文本
输出: -o/--output 指定的文件，或 stdout

做的事:
1. markdown → HTML (markdown-it-py)
2. 套用 SMP 标准排版模板（字号/颜色/间距）
3. 把 <style> 块里的规则 inline 到每个元素
4. 输出单文件 HTML

设计原则:
- 0 外部 CSS / 0 外部字体
- 所有 style 都 inline
- 移动优先（基准 375px）
- 不调 LLM、不调外部 API

注意: 不要把 draft JSON 文件当作 positional input 传入！
- 错: render.py drafts/wechat.json   ← 会把整个 JSON 当 markdown 渲染
- 对: render.py --from-draft drafts/wechat.json   ← 自动抽 body_markdown + title
- 对: render.py article.md                          ← 纯 markdown 文件
"""
import argparse
import re
import sys
from pathlib import Path

from markdown_it import MarkdownIt
from bs4 import BeautifulSoup

# SMP 标准排版（移动优先，中文友好）
SMP_BASE_CSS = """
body { font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif; color: #333; line-height: 1.7; max-width: 100%; padding: 16px; margin: 0; }
h1 { font-size: 1.875em; font-weight: 700; margin: 1.2em 0 0.6em; line-height: 1.3; }
h2 { font-size: 1.5em; font-weight: 700; margin: 1.2em 0 0.5em; line-height: 1.3; border-bottom: 1px solid #eee; padding-bottom: 0.3em; }
h3 { font-size: 1.25em; font-weight: 600; margin: 1.1em 0 0.5em; }
h4 { font-size: 1.125em; font-weight: 600; margin: 1em 0 0.4em; }
p { margin: 0.8em 0; font-size: 16px; }
a { color: #0066cc; text-decoration: none; }
strong { font-weight: 700; }
em { font-style: italic; }
ul, ol { margin: 0.8em 0; padding-left: 1.5em; }
li { margin: 0.3em 0; }
blockquote { border-left: 4px solid #ddd; background: #f9f9f9; margin: 1em 0; padding: 0.8em 1em; color: #555; }
code { background: #f4f4f4; padding: 0.15em 0.35em; border-radius: 3px; font-family: "SF Mono", Consolas, monospace; font-size: 0.9em; color: #c7254e; }
pre { background: #2d2d2d; color: #f8f8f2; padding: 1em; border-radius: 6px; overflow-x: auto; line-height: 1.5; margin: 1em 0; }
pre code { background: transparent; padding: 0; color: inherit; font-size: 0.875em; }
img { max-width: 100%; height: auto; display: block; margin: 1em auto; }
table { border-collapse: collapse; width: 100%; margin: 1em 0; }
th, td { border: 1px solid #ddd; padding: 0.5em 0.8em; text-align: left; }
th { background: #f5f5f5; font-weight: 600; }
hr { border: none; border-top: 1px solid #eee; margin: 1.5em 0; }
figcaption { text-align: center; color: #888; font-size: 0.875em; margin-top: 0.5em; }
"""


def parse_css_declarations(css: str) -> dict:
    """
    极简 CSS 解析：只支持 'selector { prop: val; prop: val; }' 这种形式
    不支持 @media / @import / 嵌套 / CSS 变量
    """
    rules = {}  # selector -> { prop: val }
    # 移除注释
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    # 匹配 selector { ... }
    pattern = re.compile(r"([^{}]+)\{([^{}]*)\}")
    for m in pattern.finditer(css):
        selector = m.group(1).strip()
        body = m.group(2).strip()
        decls = {}
        for decl in body.split(";"):
            decl = decl.strip()
            if not decl or ":" not in decl:
                continue
            prop, val = decl.split(":", 1)
            decls[prop.strip()] = val.strip()
        if decls:
            rules[selector] = decls
    return rules


def selector_matches(selector: str, element) -> bool:
    """
    支持: tag, tag.class, .class, tag#id, #id
    不支持: 组合选择器（后代 / 子 / 兄弟）+ 伪类
    """
    selector = selector.strip()
    # 复合选择器（"a, b"）拆开
    if "," in selector:
        return any(selector_matches(s, element) for s in selector.split(","))
    # 解析 tag / class / id
    tag_match = re.match(r"^([a-zA-Z][a-zA-Z0-9]*)", selector)
    tag = tag_match.group(1) if tag_match else None
    rest = selector[len(tag):] if tag else selector

    # tag check
    if tag and element.name != tag:
        return False

    # class check
    classes = re.findall(r"\.([a-zA-Z0-9_-]+)", rest)
    if classes:
        el_classes = element.get("class") or []
        if isinstance(el_classes, str):
            el_classes = el_classes.split()
        if not all(c in el_classes for c in classes):
            return False

    # id check
    id_match = re.search(r"#([a-zA-Z0-9_-]+)", rest)
    if id_match:
        if element.get("id") != id_match.group(1):
            return False

    return True


def inline_styles(soup: BeautifulSoup, css_rules: dict) -> None:
    """把 css_rules 里所有匹配的规则 inline 到元素的 style 属性"""
    for element in soup.find_all(True):
        # 跳过 <html> / <head> 等结构标签
        if element.name in ("html", "head", "meta", "title", "style", "script"):
            continue
        merged = []
        # element 自己的 style 属性作为基底
        existing = element.get("style", "").strip()
        if existing:
            merged.append(existing.rstrip(";"))
        # 应用所有匹配的规则
        for selector, decls in css_rules.items():
            if selector_matches(selector, element):
                for prop, val in decls.items():
                    merged.append(f"{prop}: {val}")
        if merged:
            # 去重（同 prop 后写覆盖前写）
            seen = {}
            for d in merged:
                if ":" in d:
                    p, v = d.split(":", 1)
                    seen[p.strip()] = v.strip()
            element["style"] = "; ".join(f"{k}: {v}" for k, v in seen.items())


def render_markdown(md_text: str, title: str | None = None) -> str:
    """markdown → inline HTML"""
    md = MarkdownIt("commonmark", {"breaks": False, "html": True}).enable("table")
    body_html = md.render(md_text)

    # 包成完整 HTML 文档
    full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title or ''}</title>
<style>{SMP_BASE_CSS}</style>
</head>
<body>
<article class="smp-article">
{body_html}
</article>
</body>
</html>"""

    soup = BeautifulSoup(full_html, "html.parser")

    # 把 <style> 块转成 rules
    style_tag = soup.find("style")
    css_text = str(style_tag.string) if style_tag and style_tag.string else ""
    rules = parse_css_declarations(css_text)

    # inline 应用
    inline_styles(soup, rules)

    # 移除 <style> 块（已 inline 完成）
    if style_tag:
        style_tag.decompose()

    # 移除 class 属性（公众号清洗 class）
    for el in soup.find_all(True):
        if "class" in el.attrs:
            del el.attrs["class"]

    # 移除 meta / title 中的多余属性
    for el in soup.find_all(["meta", "title"]):
        el.attrs = {}

    return str(soup)


def load_draft(path: str) -> tuple:
    """
    Load a draft contract JSON and extract (title, body_markdown).

    Raises:
        FileNotFoundError: file doesn't exist
        json.JSONDecodeError: file is not valid JSON
        KeyError: JSON missing required body_markdown field
    """
    import json
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    title = data.get("title")
    body = data.get("body_markdown")
    if body is None:
        raise KeyError(
            f"draft at {path} is missing required field 'body_markdown'. "
            f"Got keys: {list(data.keys())}"
        )
    return title, body


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Render markdown to inline HTML. Use --from-draft to auto-extract from a draft JSON."
    )
    src = ap.add_mutually_exclusive_group()
    src.add_argument(
        "--from-draft",
        metavar="DRAFT_JSON",
        help="Load body_markdown + title from a draft contract JSON (RECOMMENDED for subagent use)",
    )
    src.add_argument(
        "input",
        nargs="?",
        help="input markdown file (default: stdin). Do NOT pass a draft JSON here.",
    )
    ap.add_argument("-o", "--output", help="output HTML file (default: stdout)")
    ap.add_argument("--title", help="article title (used in <title> tag). Overrides draft title if --from-draft is set.")
    args = ap.parse_args()

    if args.from_draft:
        draft_title, md_text = load_draft(args.from_draft)
        # 优先用 CLI --title 覆盖 draft title
        title = args.title or draft_title
    elif args.input:
        # P0-A 防护: 拒绝把 draft JSON 文件当 markdown positional 传入
        # 否则整个 JSON 会被当 markdown 渲染，产物是 raw JSON 字符
        try:
            text = Path(args.input).read_text(encoding="utf-8")
        except (FileNotFoundError, IsADirectoryError) as e:
            ap.error(f"cannot read input file: {e}")
        stripped = text.lstrip()
        if stripped.startswith("{") and '"body_markdown"' in stripped[:200]:
            ap.error(
                f"input file {args.input} looks like a draft JSON contract, not a markdown file. "
                f"Use --from-draft to auto-extract body_markdown + title. "
                f"See 'render.py --help' for details."
            )
        md_text = text
        title = args.title
    else:
        md_text = sys.stdin.read()
        title = args.title

    html = render_markdown(md_text, title=title)

    if args.output:
        Path(args.output).write_text(html, encoding="utf-8")
        print(f"wrote {args.output} ({len(html)} bytes)", file=sys.stderr)
    else:
        print(html)


if __name__ == "__main__":
    main()
