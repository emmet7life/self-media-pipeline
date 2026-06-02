#!/usr/bin/env python3
from __future__ import annotations
"""
stdlib-only markdown → HTML renderer with inline CSS.
Replaces render.py to eliminate dependency on markdown-it-py and beautifulsoup4.
"""
import argparse
import html
import json
import re
import sys
from pathlib import Path

SMP_BASE_CSS = """
body { font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif; color: #333; line-height: 1.7; max-width: 100%; padding: 16px; margin: 0; background: #fff; }
h1 { font-size: 1.875em; font-weight: 700; margin: 1.2em 0 0.6em; line-height: 1.3; }
h2 { font-size: 1.5em; font-weight: 700; margin: 1.2em 0 0.5em; line-height: 1.3; border-bottom: 1px solid #eee; padding-bottom: 0.3em; }
h3 { font-size: 1.25em; font-weight: 600; margin: 1.1em 0 0.5em; }
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
""".strip()


def parse_css(css: str) -> list[tuple[str, dict[str, str]]]:
    """Parse simple CSS rules. Returns [(selector, {prop: val}), ...]."""
    rules = []
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.DOTALL)
    for m in re.finditer(r'([^{}]+)\{([^{}]*)\}', css):
        selector = m.group(1).strip()
        decls = {}
        for d in m.group(2).split(';'):
            d = d.strip()
            if ':' in d:
                p, v = d.split(':', 1)
                decls[p.strip()] = v.strip()
        rules.append((selector, decls))
    return rules


def selector_matches(selector: str, tag: str) -> bool:
    """Check if selector (tag or .class or combination) matches a tag name."""
    s = selector.strip()
    parts = [p.strip() for p in s.split(',')]
    for part in parts:
        t_match = re.match(r'^([a-zA-Z][a-zA-Z0-9]*)', part)
        t = t_match.group(1) if t_match else None
        if t and t != tag:
            continue
        rest = part[len(t):] if t else part
        if not re.findall(r'\.[a-zA-Z0-9_-]+', rest) and not re.search(r'#[a-zA-Z0-9_-]+', rest):
            return True
    return False


def apply_inline(match: re.Match) -> str:
    """Apply inline formatting based on context. We handle this differently."""
    return match.group(0)


def render_inline(text: str) -> str:
    """Render inline markdown to HTML."""
    text = html.escape(text, quote=False)
    # Code first (don't process inside code)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    # Images before links so ![alt](src) is not parsed as a plain link.
    text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1" />', text)
    # Bold
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    # Italic
    text = re.sub(r'(?<!\*)\*([^*\n]+)\*(?!\*)', r'<em>\1</em>', text)
    # Links
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    return text


def render_markdown(md_text: str, title: str | None = None) -> str:
    """Convert markdown to inline-style HTML."""
    lines = md_text.split('\n')
    out = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        if not line.strip():
            i += 1
            continue

        # Code block (```)
        if line.strip().startswith('```'):
            lang = line.strip()[3:].strip()
            i += 1
            code_lines = []
            while i < n and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip ```
            code_html = html.escape('\n'.join(code_lines))
            out.append(f'<pre><code>{code_html}</code></pre>')
            continue

        # Horizontal rule
        if re.match(r'^[-*_]{3,}\s*$', line.strip()):
            out.append('<hr />')
            i += 1
            continue

        # Table
        if line.strip().startswith('|'):
            table_rows = []
            while i < n and lines[i].strip().startswith('|'):
                table_rows.append(lines[i].strip())
                i += 1
            if len(table_rows) >= 2:
                out.append('<table>')
                headers = [h.strip() for h in table_rows[0].split('|') if h.strip()]
                out.append('  <thead><tr>')
                for h in headers:
                    out.append(f'    <th>{render_inline(h)}</th>')
                out.append('  </tr></thead>')
                if len(table_rows) > 2:
                    out.append('  <tbody>')
                    for row in table_rows[2:]:
                        cells = [c.strip() for c in row.split('|') if c.strip()]
                        out.append('    <tr>')
                        for c in cells:
                            out.append(f'      <td>{render_inline(c)}</td>')
                        out.append('    </tr>')
                    out.append('  </tbody>')
                out.append('</table>')
            continue

        # Heading
        hm = re.match(r'^(#{1,6})\s+(.+)$', line.strip())
        if hm:
            level = len(hm.group(1))
            content = render_inline(hm.group(2))
            out.append(f'<h{level}>{content}</h{level}>')
            i += 1
            continue

        # Blockquote
        if line.strip().startswith('> '):
            bq_lines = []
            while i < n and lines[i].strip().startswith('> '):
                bq_lines.append(lines[i].strip()[2:])
                i += 1
            out.append(f'<blockquote><p>{render_inline(" ".join(bq_lines))}</p></blockquote>')
            continue

        # Unordered list
        if re.match(r'^[-*+]\s+', line.strip()):
            out.append('<ul>')
            while i < n and re.match(r'^[-*+]\s+', lines[i].strip()):
                content = re.sub(r'^[-*+]\s+', '', lines[i].strip())
                out.append(f'  <li>{render_inline(content)}</li>')
                i += 1
            out.append('</ul>')
            continue

        # Ordered list
        if re.match(r'^\d+[.)]\s+', line.strip()):
            out.append('<ol>')
            while i < n and re.match(r'^\d+[.)]\s+', lines[i].strip()):
                content = re.sub(r'^\d+[.)]\s+', '', lines[i].strip())
                out.append(f'  <li>{render_inline(content)}</li>')
                i += 1
            out.append('</ol>')
            continue

        # Paragraph
        para_lines = []
        while i < n and lines[i].strip():
            # Non-empty line
            line_content = lines[i]
            # Check for block elements inside paragraph
            if re.match(r'^#{1,6}\s+', line_content.strip()) or line_content.strip().startswith('```') or re.match(r'^[-*+]\s+', line_content.strip()) or re.match(r'^\d+[.)]\s+', line_content.strip()) or re.match(r'^\[/[-*_]{3,}\s*$', line_content.strip()) or line_content.strip().startswith('|') or line_content.strip().startswith('> '):
                break
            para_lines.append(line_content)
            i += 1

        while i < n and not lines[i].strip():
            i += 1

        if para_lines:
            clean = ' '.join(l.strip() for l in para_lines if l.strip())
            out.append(f'<p>{render_inline(clean)}</p>')

    body_html = '\n'.join(out)

    full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title or '')}</title>
<style>
{SMP_BASE_CSS}
</style>
</head>
<body>
<article>
{body_html}
</article>
</body>
</html>"""

    # Inline the CSS rules
    rules = parse_css(SMP_BASE_CSS)
    # Simple inline: apply matching CSS rules inline
    # For a PoC, we wrap with the full style block and also inline key properties
    result_lines = []
    for line in full_html.split('\n'):
        m = re.match(r'^<([a-z0-9]+)([^>]*)>', line)
        if m:
            tag = m.group(1)
            attrs_str = m.group(2)
            style_attrs = []
            for sel, decls in rules:
                if selector_matches(sel, tag):
                    for prop, val in decls.items():
                        style_attrs.append(f'{prop}: {val}')
            if style_attrs:
                existing_style = ''
                sm = re.search(r'style="([^"]*)"', attrs_str)
                if sm:
                    existing_style = sm.group(1)
                all_style = existing_style + '; ' + '; '.join(style_attrs) if existing_style else '; '.join(style_attrs)
                escaped_style = html.escape(all_style, quote=True)
                if sm:
                    attrs_str = attrs_str[:sm.start()] + f' style="{escaped_style}"' + attrs_str[sm.end():]
                else:
                    attrs_str += f' style="{escaped_style}"'
                line = f'<{tag}{attrs_str}>' + line[m.end():]
        result_lines.append(line)

    return '\n'.join(result_lines)


def load_draft(path: str) -> tuple[str | None, str]:
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if 'body_markdown' not in data:
        raise KeyError(
            f"draft at {path} is missing required field 'body_markdown'. "
            f"Got keys: {list(data.keys())}"
        )
    return data.get('title'), data['body_markdown']


def main() -> None:
    ap = argparse.ArgumentParser(description="Render markdown to HTML (stdlib only)")
    src = ap.add_mutually_exclusive_group()
    src.add_argument('--from-draft', metavar='DRAFT_JSON', help='Load from draft JSON')
    src.add_argument('input', nargs='?', help='Input markdown file (or stdin)')
    ap.add_argument('-o', '--output', help='Output HTML file')
    ap.add_argument('--title', help='Article title')
    args = ap.parse_args()

    if args.from_draft:
        try:
            draft_title, md_text = load_draft(args.from_draft)
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as exc:
            ap.error(str(exc))
        title = args.title or draft_title or ''
    elif args.input:
        try:
            md_text = Path(args.input).read_text(encoding='utf-8')
        except (FileNotFoundError, IsADirectoryError) as exc:
            ap.error(f"cannot read input file: {exc}")
        stripped = md_text.lstrip()
        if stripped.startswith('{') and '"body_markdown"' in stripped[:500]:
            ap.error(
                f"input file {args.input} looks like a draft JSON contract, not a markdown file. "
                f"Use --from-draft to extract body_markdown and title."
            )
        title = args.title or ''
    else:
        md_text = sys.stdin.read()
        title = args.title or ''

    html = render_markdown(md_text, title=title)

    if args.output:
        Path(args.output).write_text(html, encoding='utf-8')
        print(f'wrote {args.output} ({len(html)} bytes)', file=sys.stderr)
    else:
        print(html)


if __name__ == '__main__':
    main()
