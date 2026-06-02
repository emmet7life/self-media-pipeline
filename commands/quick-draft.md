---
description: "Draft publishable self-media assets with explicit platform and template selection."
argument-hint: "[topic/source] [--platforms=wechat,xiaohongshu] [--templates=wechat=wechat-magazine-editorial,...]"
allowed-tools: Read, Write, Edit, Bash(python3:*), Bash(./tools/*), Bash(ls:*), Bash(find:*)
---

# /quick-draft

You are the self-media-pipeline orchestrator. Turn the user's topic, draft, URL, or brief into one or more publishable platform assets by coordinating platform selection, template selection, writer/reviewer/adapter/renderer work, and library insertion.

## Required Intake

Parse `$ARGUMENTS` for:

- `topic` or source material.
- `platforms`: comma-separated platform IDs.
- `templates`: comma-separated `platform=template-id` mappings.
- optional `word_count`, `source`, and `style_reference`.

If `platforms` is missing, run:

```bash
python3 tools/list-targets --active-only --json
```

Ask the user which active/selectable platform(s) to output. Do not offer planned platforms as choices.

If templates are missing for any selected platform, run:

```bash
python3 tools/list-templates --platform <platform> --json
```

For each selected platform, show the available template IDs with their short descriptions and ask the user to choose one. If there is exactly one default template for that platform, use it automatically and tell the user which template is being applied.

## Spec Creation

After platform and template selection is complete, create the run spec with `tools/draft-spec`:

```bash
python3 tools/draft-spec \
  --topic "<topic>" \
  --platforms "<platforms>" \
  --templates "<platform=template-id,...>" \
  --out examples/<timestamp>/spec.json
```

The spec must include:

```json
{
  "target_platforms": ["wechat", "xiaohongshu"],
  "template_selection": {
    "wechat": "wechat-magazine-editorial",
    "xiaohongshu": "xhs-pastel-card-deck"
  }
}
```

## Orchestration

For each target platform:

1. Load `skills/platform-<platform>/SKILL.md`, `constraints.json`, `skills/template-library/SKILL.md`, and the selected `templates/<template-id>/SKILL.md` plus `example.html`.
2. Spawn or perform the `writer` role to write `examples/<timestamp>/drafts/<platform>.json`.
3. Spawn or perform the `reviewer` role to write `examples/<timestamp>/reviews/<platform>.json`.
4. Render markdown to HTML, adapt it for the platform, and render PNG assets when available.
5. Insert article, drafts, and derivatives into the content library.

Use:

```bash
python3 tools/run-pipeline --spec examples/<timestamp>/spec.json --real-llm
```

If Chromium/Playwright is unavailable, keep the HTML artifacts and report that PNG rendering needs `python3 -m playwright install chromium`.

## Output

Report:

- `article_id`
- selected platforms and template IDs
- per-platform draft status
- generated HTML/PNG artifact paths
- review warnings or blocks

Never proceed with an unknown platform, inactive platform, unknown template, or template that belongs to a different platform.
