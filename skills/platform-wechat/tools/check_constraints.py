#!/usr/bin/env python3
"""
check_constraints.py —— 微信公众号草稿硬约束自检

输入: draft.json (writer subagent 产出)
       读 ../constraints.json 拿硬约束
输出: JSON 报告

report schema:
{
  "pass": true | false,
  "issues": [
    {"constraint": "...", "severity": "block|warn|info", "message": "...", "location": "..."}
  ],
  "summary": {"block": 0, "warn": 0, "info": 0}
}
"""
import argparse
import json
import re
import sys
from pathlib import Path

DEFAULT_CONSTRAINTS = Path(__file__).parent.parent / "constraints.json"


def load_constraints(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check_draft(draft: dict, constraints: dict) -> dict:
    issues = []
    title = draft.get("title", "") or ""
    body = draft.get("body_markdown", "") or ""
    images = draft.get("images", []) or []

    # 字数
    wc = constraints.get("word_count", {})
    body_len = len(body)
    if body_len < wc.get("body_min", 0):
        issues.append({"constraint": "word_count.body_min", "severity": "block", "message": f"body {body_len} chars < min {wc.get('body_min')}"})
    if body_len > wc.get("body_max", 99999):
        issues.append({"constraint": "word_count.body_max", "severity": "block", "message": f"body {body_len} chars > max {wc.get('body_max')}"})
    if wc.get("body_recommended_min", 0) <= body_len <= wc.get("body_recommended_max", 99999):
        pass  # 在推荐区间
    elif body_len:
        issues.append({"constraint": "word_count.recommended_range", "severity": "info", "message": f"body {body_len} chars outside recommended [{wc.get('body_recommended_min')}, {wc.get('body_recommended_max')}]"})

    # 标题
    title_len = len(title)
    if title_len < wc.get("title_min", 0):
        issues.append({"constraint": "word_count.title_min", "severity": "block", "message": f"title {title_len} chars < min {wc.get('title_min')}"})
    if title_len > wc.get("title_max", 99999):
        issues.append({"constraint": "word_count.title_max", "severity": "block", "message": f"title {title_len} chars > max {wc.get('title_max')}"})

    # 段落长度（粗略：连续 \n\n 之间取最长行数）
    paragraphs = [p for p in body.split("\n\n") if p.strip()]
    para_max_lines = wc.get("paragraph_max_lines", 5)
    for i, p in enumerate(paragraphs):
        line_count = len([ln for ln in p.split("\n") if ln.strip()])
        if line_count > para_max_lines:
            issues.append({"constraint": "word_count.paragraph_max_lines", "severity": "warn", "message": f"paragraph {i+1} has {line_count} lines > max {para_max_lines}", "location": p[:60] + "..."})

    # 配图密度（结构约束）
    struct = constraints.get("structure", {})
    if body and images:
        image_every = struct.get("image_every_chars", [600, 1000])
        avg_chars_per_image = body_len / len(images)
        if avg_chars_per_image > image_every[1]:
            issues.append({"constraint": "structure.image_density_too_low", "severity": "warn", "message": f"{len(images)} images for {body_len} chars (avg {avg_chars_per_image:.0f}/image > {image_every[1]})"})
        if avg_chars_per_image < image_every[0]:
            issues.append({"constraint": "structure.image_density_too_high", "severity": "info", "message": f"{len(images)} images for {body_len} chars (avg {avg_chars_per_image:.0f}/image < {image_every[0]})"})

    # 小标题密度
    subtitle_every = struct.get("subtitle_every_chars", [300, 500])
    h2_count = body.count("\n## ") + (1 if body.startswith("## ") else 0)
    if body and h2_count:
        avg_chars_per_h2 = body_len / h2_count
        if avg_chars_per_h2 > subtitle_every[1]:
            issues.append({"constraint": "structure.subtitle_density_too_low", "severity": "warn", "message": f"{h2_count} h2 for {body_len} chars (avg {avg_chars_per_h2:.0f}/h2 > {subtitle_every[1]})"})

    # 危险标签（head 区域必要的 meta 例外）
    inline_html = draft.get("inline_html", "") or ""
    forbidden = constraints.get("tags_forbidden", [])
    for tag in forbidden:
        # 检查简化的 forbidden 标签名（"script", "link[rel=stylesheet]", "meta"）
        if tag == "script":
            if "<script" in inline_html.lower():
                issues.append({"constraint": f"forbidden_tag.{tag}", "severity": "block", "message": f"<{tag}> still present in inline_html"})
        elif tag == "meta":
            # head 里的 meta charset / viewport 是允许的；只检测 body 区域的 meta
            # 简化：取 </head> 之后的部分
            head_end = inline_html.lower().find("</head>")
            body_part = inline_html[head_end:] if head_end >= 0 else inline_html
            if "<meta" in body_part.lower():
                issues.append({"constraint": f"forbidden_tag.{tag}", "severity": "block", "message": f"<{tag}> present in body (only allowed in <head>)"})
        elif "[" in tag:
            # 复合选择器（"link[rel=stylesheet]"）—— 简单子串检测
            base = tag.split("[")[0]
            attr = tag.split("[")[1].rstrip("]")
            if f"<{base}" in inline_html.lower() and attr in inline_html.lower():
                issues.append({"constraint": f"forbidden_tag.{tag}", "severity": "block", "message": f"<{tag}> pattern present"})

    # 汇总
    summary = {"block": 0, "warn": 0, "info": 0}
    for issue in issues:
        summary[issue["severity"]] = summary.get(issue["severity"], 0) + 1

    return {
        "pass": summary["block"] == 0,
        "issues": issues,
        "summary": summary,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Check WeChat draft against hard constraints")
    ap.add_argument("draft", help="draft.json file path")
    ap.add_argument("--constraints", default=str(DEFAULT_CONSTRAINTS), help="constraints.json path")
    ap.add_argument("--out", help="output report path (default stdout)")
    args = ap.parse_args()

    draft = json.loads(Path(args.draft).read_text(encoding="utf-8"))
    constraints = load_constraints(Path(args.constraints))
    report = check_draft(draft, constraints)

    if args.out:
        Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"wrote {args.out}", file=sys.stderr)
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))

    # exit code: 0 = pass, 1 = has block
    sys.exit(0 if report["pass"] else 1)


if __name__ == "__main__":
    main()
