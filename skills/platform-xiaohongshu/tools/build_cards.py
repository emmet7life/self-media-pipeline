#!/usr/bin/env python3
"""
build_cards.py —— 把小红书 draft 拆成独立可读的卡片 HTML。

输出不是一张大图，也不是等待切片的大画布；每个 NN.html 都是一张
1080x1440 发布图的源文件，后续由 render-image/tools/render_grid.py
逐张截图生成 NN.png。
"""
import argparse
import html
import json
import re
from pathlib import Path


CARD_CSS = """
:root {
  --bg: #fff6ef;
  --paper: #fffdf8;
  --ink: #25211d;
  --muted: #776d62;
  --accent: #e95d45;
  --accent-2: #4b8c7a;
  --rule: rgba(37,33,29,.16);
  --shadow: 0 28px 80px rgba(73, 52, 39, .16);
}
* { box-sizing: border-box; }
html, body { width: 1080px; height: 1440px; margin: 0; overflow: hidden; }
body {
  background:
    radial-gradient(circle at 16% 12%, rgba(233,93,69,.16), transparent 28%),
    radial-gradient(circle at 88% 84%, rgba(75,140,122,.15), transparent 30%),
    var(--bg);
  color: var(--ink);
  font-family: Inter, "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
}
.card {
  position: relative;
  width: 1080px;
  height: 1440px;
  padding: 92px 86px 76px;
  display: flex;
  flex-direction: column;
}
.sticker {
  flex: 1;
  border: 3px dashed rgba(37,33,29,.22);
  border-radius: 44px;
  background: rgba(255,253,248,.92);
  box-shadow: var(--shadow);
  padding: 76px 72px;
  display: flex;
  flex-direction: column;
}
.kicker {
  font-size: 30px;
  letter-spacing: .16em;
  text-transform: uppercase;
  color: var(--accent);
  font-weight: 800;
  margin-bottom: 34px;
}
h1 {
  font-size: 86px;
  line-height: 1.04;
  letter-spacing: 0;
  margin: 0;
  font-weight: 900;
  max-width: 9em;
}
h2 {
  font-size: 66px;
  line-height: 1.08;
  letter-spacing: 0;
  margin: 0 0 34px;
  font-weight: 900;
}
.body {
  margin-top: 32px;
  font-size: 40px;
  line-height: 1.42;
  color: var(--ink);
}
.body p { margin: 0 0 24px; }
.body strong { color: var(--accent); font-weight: 900; }
.tags {
  margin-top: auto;
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  padding-top: 34px;
}
.tag {
  border: 2px solid var(--rule);
  border-radius: 999px;
  padding: 10px 18px;
  font-size: 26px;
  color: var(--muted);
  background: rgba(255,255,255,.66);
}
.page-num {
  position: absolute;
  right: 104px;
  bottom: 74px;
  font-size: 26px;
  font-weight: 800;
  color: var(--muted);
}
.dots {
  position: absolute;
  left: 86px;
  right: 86px;
  bottom: 78px;
  display: flex;
  justify-content: center;
  gap: 14px;
}
.dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: rgba(37,33,29,.18);
}
.dot.active { background: var(--accent); }
"""


def strip_markdown(text: str) -> str:
    text = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"__([^_]+)__", r"<strong>\1</strong>", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return text.strip()


def plain_text(text: str) -> str:
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return text.strip()


def split_sections(markdown: str) -> tuple[str, list[dict], list[str]]:
    tags = re.findall(r"#[\w\u4e00-\u9fff-]+", markdown)
    without_tags = re.sub(r"(?:^|\s)#[\w\u4e00-\u9fff-]+", "", markdown).strip()
    parts = re.split(r"\n##+\s+", without_tags)
    intro = parts[0].strip()
    sections = []
    for raw in parts[1:]:
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        if not lines:
            continue
        title = lines[0]
        body = "\n\n".join(lines[1:]).strip()
        sections.append({"title": title, "body": body})
    return intro, sections, tags


def body_html(markdown: str, max_paragraphs: int = 4) -> str:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", markdown) if p.strip()]
    out = []
    for p in paragraphs[:max_paragraphs]:
        out.append(f"<p>{strip_markdown(html.escape(p))}</p>")
    return "\n".join(out)


def make_cards(draft: dict, count: int) -> list[dict]:
    title = draft["title"]
    intro, sections, tags = split_sections(draft["body_markdown"])
    cards = [{
        "kind": "cover",
        "title": title,
        "kicker": "XIAOHONGSHU NOTE",
        "body": intro or "今天这篇，帮你快速抓住重点。",
        "tags": tags[:5],
    }]

    for i, section in enumerate(sections, start=1):
        cards.append({
            "kind": "content",
            "title": section["title"],
            "kicker": f"PART {i:02d}",
            "body": section["body"] or section["title"],
            "tags": tags[:5],
        })
        if len(cards) >= count:
            break

    filler_cards = [
        {
            "kind": "summary",
            "title": "最后总结 💡",
            "kicker": "SAVE THIS",
            "body": "这篇可以先收藏，真正上手时按步骤逐个检查。评论区也可以继续补充你的使用场景。",
        },
        {
            "kind": "summary",
            "title": "适合谁看 👀",
            "kicker": "FOR YOU",
            "body": "如果你正在入门、整理方法论、或者想把知识变成可执行流程，这组卡片可以直接当检查清单。",
        },
        {
            "kind": "summary",
            "title": "怎么用 ✅",
            "kicker": "NEXT STEP",
            "body": "先照着步骤跑一遍，再把卡片里的关键词替换成你的真实业务场景，不要一开始就追求复杂。",
        },
        {
            "kind": "summary",
            "title": "收藏提醒 📌",
            "kicker": "CTA",
            "body": "需要的时候回来对照：标题、步骤、避坑、总结，一个都别漏。",
        },
    ]
    filler_i = 0
    while len(cards) < count:
        card = dict(filler_cards[filler_i % len(filler_cards)])
        card["tags"] = tags[:5]
        cards.append(card)
        filler_i += 1

    return cards[:count]


def render_card(card: dict, index: int, total: int) -> str:
    dots = "".join(f"<span class='dot {'active' if i == index else ''}'></span>" for i in range(1, total + 1))
    tags = "".join(f"<span class='tag'>{html.escape(t)}</span>" for t in card.get("tags", []))
    safe_title = html.escape(plain_text(card["title"]))
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title} · {index:02d}</title>
  <style>{CARD_CSS}</style>
</head>
<body>
  <main class="card">
    <section class="sticker">
      <div class="kicker">{html.escape(card["kicker"])}</div>
      {'<h1>' if card['kind'] == 'cover' else '<h2>'}{safe_title}{'</h1>' if card['kind'] == 'cover' else '</h2>'}
      <div class="body">{body_html(card["body"])}</div>
      <div class="tags">{tags}</div>
    </section>
    <div class="dots">{dots}</div>
    <div class="page-num">{index:02d}/{total:02d}</div>
  </main>
</body>
</html>
"""


def build_cards(draft_path: Path, output_dir: Path, count: int) -> dict:
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    output_dir.mkdir(parents=True, exist_ok=True)
    cards = make_cards(draft, count)
    html_paths = []
    for i, card in enumerate(cards, start=1):
        html_path = output_dir / f"{i:02d}.html"
        html_path.write_text(render_card(card, i, len(cards)), encoding="utf-8")
        html_paths.append(str(html_path))
    manifest = {
        "draft": str(draft_path),
        "count": len(html_paths),
        "card_html": html_paths,
        "size": {"width_px": 1080, "height_px": 1440},
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    ap = argparse.ArgumentParser(description="Build independent Xiaohongshu card HTML files from a draft JSON")
    ap.add_argument("--draft", required=True, help="draft JSON path")
    ap.add_argument("--output-dir", required=True, help="directory for NN.html files")
    ap.add_argument("--count", type=int, default=9, help="target card count, 1-9")
    args = ap.parse_args()
    count = max(1, min(args.count, 9))
    manifest = build_cards(Path(args.draft), Path(args.output_dir), count)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
