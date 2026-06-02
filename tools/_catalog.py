#!/usr/bin/env python3
from __future__ import annotations

"""Shared platform/template catalog helpers for self-media-pipeline tools."""

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"
TEMPLATES_DIR = ROOT / "templates"

PLATFORM_NAMES = {
    "wechat": "微信公众号",
    "xiaohongshu": "小红书",
}

PLANNED_PLATFORMS = [
    {
        "id": "zhihu",
        "name": "知乎",
        "skill_dir": None,
        "constraints": None,
        "status": "planned",
        "selectable": False,
        "note": "第 9+ 周评估",
    },
    {
        "id": "bilibili",
        "name": "B 站专栏",
        "skill_dir": None,
        "constraints": None,
        "status": "planned",
        "selectable": False,
        "note": "第 9+ 周评估",
    },
    {
        "id": "weibo",
        "name": "微博",
        "skill_dir": None,
        "constraints": None,
        "status": "planned",
        "selectable": False,
        "note": "第 9+ 周评估",
    },
]


def parse_frontmatter(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    match = re.match(r"---\s*\n(.*?)\n---", raw, flags=re.S)
    data: dict[str, Any] = {}
    if not match:
        return data
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = parse_frontmatter_value(value.strip())
    return data


def parse_frontmatter_value(value: str) -> Any:
    value = value.strip().strip('"').strip("'")
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    return value


def platform_constraints(platform_id: str) -> dict[str, Any]:
    path = SKILLS_DIR / f"platform-{platform_id}" / "constraints.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def platform_defaults(platform_id: str) -> dict[str, Any]:
    constraints = platform_constraints(platform_id)
    if platform_id == "wechat":
        word_count = constraints.get("word_count", {})
        return {
            "max_chars": word_count.get("body_max", 5000),
            "inline_css_only": constraints.get("font_reference_forbidden", True),
        }
    if platform_id == "xiaohongshu":
        body = constraints.get("body", {})
        grid = constraints.get("images", {}).get("grid", {})
        cover = constraints.get("images", {}).get("cover", {})
        return {
            "max_chars": body.get("max", 1000),
            "grid": f"{grid.get('rows', 3)}x{grid.get('cols', 3)}",
            "cover_size": f"{cover.get('width_px', 1080)}x{cover.get('height_px', 1440)}",
        }
    return {}


def list_platforms(include_planned: bool = True) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for constraints_path in sorted(SKILLS_DIR.glob("platform-*/constraints.json")):
        skill_dir = constraints_path.parent
        platform_id = skill_dir.name.removeprefix("platform-")
        tools_dir = skill_dir / "tools"
        tools = [
            str(path.relative_to(ROOT))
            for path in sorted(tools_dir.glob("*.py"))
        ] if tools_dir.exists() else []
        rows.append({
            "id": platform_id,
            "name": PLATFORM_NAMES.get(platform_id, platform_id),
            "skill_dir": str(skill_dir.relative_to(ROOT)),
            "constraints": str(constraints_path.relative_to(ROOT)),
            "status": "active",
            "selectable": True,
            "tools_implemented": tools,
            "tools_planned": [],
            "note": "工具层实现完成",
            "defaults": platform_defaults(platform_id),
        })
    if include_planned:
        rows.extend(PLANNED_PLATFORMS)
    return rows


def active_platform_ids() -> list[str]:
    return [row["id"] for row in list_platforms(include_planned=False)]


def list_templates(platform: str | None = None, include_inactive: bool = False) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for skill_path in sorted(TEMPLATES_DIR.glob("*/SKILL.md")):
        template_id = skill_path.parent.name
        fm = parse_frontmatter(skill_path)
        status = str(fm.get("status", "active"))
        if status != "active" and not include_inactive:
            continue
        template_platform = str(fm.get("platform", ""))
        if platform and template_platform != platform:
            continue
        rows.append({
            "id": template_id,
            "name": str(fm.get("name", template_id)),
            "platform": template_platform,
            "description": str(fm.get("description", "")),
            "status": status,
            "default": bool(fm.get("default", False)),
            "content_type": str(fm.get("content_type", "")),
            "output_kind": str(fm.get("output_kind", "")),
            "skill_path": str(skill_path.relative_to(ROOT)),
            "example_path": str((skill_path.parent / "example.html").relative_to(ROOT)),
            "has_example": (skill_path.parent / "example.html").exists(),
        })
    return rows


def template_by_id(template_id: str) -> dict[str, Any] | None:
    for template in list_templates(include_inactive=True):
        if template["id"] == template_id:
            return template
    return None


def default_template_for_platform(platform_id: str) -> str | None:
    defaults = [
        template["id"]
        for template in list_templates(platform=platform_id)
        if template["default"]
    ]
    if len(defaults) == 1:
        return defaults[0]
    return None


def parse_template_selection(raw: str | None) -> dict[str, str]:
    if not raw:
        return {}
    selection: dict[str, str] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair:
            continue
        if "=" not in pair:
            raise ValueError(f"invalid template mapping {pair!r}; expected platform=template-id")
        platform, template_id = pair.split("=", 1)
        platform = platform.strip()
        template_id = template_id.strip()
        if not platform or not template_id:
            raise ValueError(f"invalid template mapping {pair!r}; expected platform=template-id")
        selection[platform] = template_id
    return selection


def resolve_template_selection(platforms: list[str], provided: dict[str, str] | None = None) -> dict[str, str]:
    provided = provided or {}
    active = set(active_platform_ids())
    unknown_platforms = [platform for platform in platforms if platform not in active]
    if unknown_platforms:
        raise ValueError(f"unknown or inactive platform(s): {unknown_platforms}; active: {sorted(active)}")

    extra_platforms = [platform for platform in provided if platform not in platforms]
    if extra_platforms:
        raise ValueError(f"template selection contains platform(s) not in --platforms: {extra_platforms}")

    selection: dict[str, str] = {}
    for platform in platforms:
        template_id = provided.get(platform) or default_template_for_platform(platform)
        if not template_id:
            available = [template["id"] for template in list_templates(platform=platform)]
            raise ValueError(
                f"no default template for {platform}; choose one with --templates {platform}=<id>. "
                f"Available: {available}"
            )
        template = template_by_id(template_id)
        if not template:
            raise ValueError(f"unknown template {template_id!r} for platform {platform}")
        if template["status"] != "active":
            raise ValueError(f"template {template_id!r} is not active")
        if template["platform"] != platform:
            raise ValueError(
                f"template {template_id!r} belongs to platform {template['platform']!r}, not {platform!r}"
            )
        selection[platform] = template_id
    return selection


def validate_catalog() -> list[str]:
    issues: list[str] = []
    active = set(active_platform_ids())
    all_platforms = {row["id"] for row in list_platforms(include_planned=True)}
    templates = list_templates(include_inactive=True)

    for template in templates:
        if not template["platform"]:
            issues.append(f"template {template['id']} missing platform")
        elif template["platform"] not in all_platforms:
            issues.append(f"template {template['id']} references unknown platform {template['platform']}")
        if template["status"] == "active" and not template["has_example"]:
            issues.append(f"active template {template['id']} missing example.html")
        if not template["description"]:
            issues.append(f"template {template['id']} missing description")

    for platform in sorted(active):
        platform_templates = [
            template for template in list_templates(platform=platform)
            if template["status"] == "active"
        ]
        if not platform_templates:
            issues.append(f"active platform {platform} has no active templates")
        default_templates = [template["id"] for template in platform_templates if template["default"]]
        if len(default_templates) == 0:
            issues.append(f"active platform {platform} has no default template")
        if len(default_templates) > 1:
            issues.append(f"active platform {platform} has multiple default templates: {default_templates}")
    return issues
