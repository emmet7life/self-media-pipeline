#!/usr/bin/env python3
"""
check_constraints.py —— 小红书草稿硬约束自检

输入: draft.json
       读 ../constraints.json
输出: JSON 报告（schema 与 platform-wechat 一致）

小红书特有自检:
- 标题长度 6-20（严格）
- 标题含 emoji
- 正文 100-1000（严格上限 1000，超出折叠）
- 3-5 个 # 标签
- 1-9 张配图（推荐 4-6）
- 配图尺寸每张必须 1080x1440
- 无禁用词（"震惊"、"99% 的人不知道"）
"""
import argparse
import json
import re
import sys
from pathlib import Path

DEFAULT_CONSTRAINTS = Path(__file__).parent.parent / "constraints.json"


def has_emoji(s: str) -> bool:
    """简易 emoji 检测：检查是否含非 ASCII 字符外的特殊 Unicode 区段"""
    # 基本 emoji 范围
    emoji_pattern = re.compile(
        "["
        "\U0001F300-\U0001F9FF"  # symbols & pictographs
        "\U0001FA00-\U0001FAFF"  # symbols & pictographs extended-A
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F680-\U0001F6FF"  # transport & map
        "\U00002600-\U000027BF"  # miscellaneous symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "]+",
        flags=re.UNICODE,
    )
    return bool(emoji_pattern.search(s))


def count_hashtags(body: str) -> int:
    return len(re.findall(r"#[^\s#]+", body))


def check_draft(draft: dict, constraints: dict) -> dict:
    issues = []
    title = draft.get("title", "") or ""
    body = draft.get("body_markdown", "") or ""
    images = draft.get("images", []) or []

    # 标题
    t = constraints.get("title", {})
    title_len = len(title)
    if title_len < t.get("min", 0):
        issues.append({"constraint": "title.min", "severity": "block", "message": f"title {title_len} chars < min {t.get('min')}"})
    if title_len > t.get("max", 99999):
        issues.append({"constraint": "title.max", "severity": "block", "message": f"title {title_len} chars > max {t.get('max')}"})
    if t.get("require_emoji") and not has_emoji(title):
        issues.append({"constraint": "title.require_emoji", "severity": "block", "message": "title missing emoji"})

    # 正文
    b = constraints.get("body", {})
    body_len = len(body)
    if body_len < b.get("min", 0):
        issues.append({"constraint": "body.min", "severity": "block", "message": f"body {body_len} chars < min {b.get('min')}"})
    if body_len > b.get("max", 99999):
        issues.append({"constraint": "body.max", "severity": "block", "message": f"body {body_len} chars > max {b.get('max')} (会被折叠)"})

    # 段落长度
    para_max = b.get("paragraph_max_lines", 3)
    for i, p in enumerate([p for p in body.split("\n\n") if p.strip()]):
        line_count = len([ln for ln in p.split("\n") if ln.strip()])
        if line_count > para_max:
            issues.append({"constraint": "body.paragraph_max_lines", "severity": "warn", "message": f"paragraph {i+1} has {line_count} lines > max {para_max}", "location": p[:60] + "..."})

    # 话题标签
    tag_count = count_hashtags(body)
    if tag_count < b.get("min_hashtags", 0):
        issues.append({"constraint": "body.min_hashtags", "severity": "block", "message": f"only {tag_count} hashtags < min {b.get('min_hashtags')}"})
    if tag_count > b.get("max_hashtags", 99):
        issues.append({"constraint": "body.max_hashtags", "severity": "warn", "message": f"{tag_count} hashtags > max {b.get('max_hashtags')} (推荐 3-5)"})

    # 配图
    img_cfg = constraints.get("images", {})
    cover = img_cfg.get("cover", {})
    grid = img_cfg.get("grid", {})
    img_count = len(images)
    if img_count < grid.get("count_min", 0):
        issues.append({"constraint": "images.count_min", "severity": "block", "message": f"{img_count} images < min {grid.get('count_min')}"})
    if img_count > grid.get("count_max", 999):
        issues.append({"constraint": "images.count_max", "severity": "block", "message": f"{img_count} images > max {grid.get('count_max')}"})
    if grid.get("count_recommended_min", 0) <= img_count <= grid.get("count_recommended_max", 999):
        pass
    elif img_count:
        rec_min = grid.get("count_recommended_min")
        rec_max = grid.get("count_recommended_max")
        issues.append({"constraint": "images.recommended_range", "severity": "info", "message": f"{img_count} images outside recommended [{rec_min}, {rec_max}]"})

    # 配图尺寸自检（仅当 draft 里 images 带了 size 字段）
    for i, im in enumerate(images):
        w = im.get("width_px")
        h = im.get("height_px")
        if w and h and (w != cover.get("width_px") or h != cover.get("height_px")):
            issues.append({"constraint": "images.cover_size", "severity": "block", "message": f"image {i+1} is {w}x{h}, expected {cover.get('width_px')}x{cover.get('height_px')}"})

    # 禁用词（点击诱饵）
    for word in constraints.get("forbidden", {}).get("clickbait_words", []):
        if word in body or word in title:
            issues.append({"constraint": f"forbidden.clickbait.{word}", "severity": "block", "message": f"clickbait word '{word}' present"})

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
    ap = argparse.ArgumentParser(description="Check Xiaohongshu draft against hard constraints")
    ap.add_argument("draft")
    ap.add_argument("--constraints", default=str(DEFAULT_CONSTRAINTS))
    ap.add_argument("--out")
    args = ap.parse_args()

    draft = json.loads(Path(args.draft).read_text(encoding="utf-8"))
    constraints = json.loads(Path(args.constraints).read_text(encoding="utf-8"))
    report = check_draft(draft, constraints)

    if args.out:
        Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"wrote {args.out}", file=sys.stderr)
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))

    sys.exit(0 if report["pass"] else 1)


if __name__ == "__main__":
    main()
