---
description: "Quickly draft a self-media article for a topic. Spawns the writer subagent for each target platform (WeChat + Xiaohongshu by default), then runs reviewer + platform-adapter + renderer. End-to-end in one slash command."
---

# /quick-draft

## What it does

Take a topic (or short brief) from the user, run the full self-media-pipeline end-to-end:
1. Parse the topic into a spec (use `tools/draft-spec`)
2. Spawn `writer` subagent for each target platform (default: wechat + xiaohongshu)
3. Spawn `reviewer` subagent for each draft
4. Spawn `platform-adapter` subagent for each platform-adapted HTML
5. Spawn `renderer` subagent for each platform's image assets
6. Insert everything into the L1 content library via `library-mcp` tools

## Usage

```
/quick-draft 写一篇关于 [topic] 的公众号 + 小红书
/quick-draft "AI Agent 入门" --platforms=wechat,xiaohongshu --word-count=800
/quick-draft --source "https://lilianweng.github.io/posts/2023-06-23-agent/" --topic "AI Agent 入门"
```

## Inputs

- `topic` (string, required): what to write about
- `platforms` (list, default: `wechat,xiaohongshu`): target platforms
- `word_count` (int, optional): target body length
- `source` (string, optional): URL or raw notes to base the draft on
- `style_reference` (string, optional): article id in library, or a style hint

## What the orchestrator does step-by-step

1. **Plan**: `tools/draft-spec --topic <T> --platforms <P> --out examples/<timestamp>/spec.json`
2. **Write**: for each platform, delegate to `writer` subagent:
   - spawn writer with task "draft <platform> article, topic=<T>, source=<S>, word_count=<W>"
   - writer loads `skills/platform-<platform>/SKILL.md` + `constraints.json` and writes `examples/<timestamp>/drafts/<platform>.json`
3. **Review**: for each draft, delegate to `reviewer` subagent:
   - spawn reviewer with task "review draft at <draft_path>, platform <platform>"
   - reviewer writes `examples/<timestamp>/reviews/<platform>.json` with pass/block/warn issues
3.5. **Render markdown → HTML** (CRITICAL step — must happen BEFORE platform-adapter):
   - for each passed draft, run `skills/render-html/tools/render.py --from-draft <draft_path> -o <run-dir>/article-<platform>.html`
   - `--from-draft` flag auto-extracts `body_markdown` + `title` from the draft JSON
   - **DO NOT** pass the draft JSON as a positional argument to `render.py` — that will render the JSON as markdown and produce garbage HTML
   - See `skills/render-html/SKILL.md` for full contract
4. **Adapt**: for each rendered HTML, delegate to `platform-adapter`:
   - spawn platform-adapter with task "adapt HTML at <render_html output> for <platform>"
   - platform-adapter invokes `skills/platform-<platform>/tools/adapt_html.py` and returns the sanitized HTML
5. **Render**: for each adapted HTML, delegate to `renderer`:
   - spawn renderer with task "render <html_path> for <platform>, output <output_dir>"
   - renderer produces PNG artifacts (cover / 9 tiles / contact sheet)
6. **Store**: insert into library:
   - `library.insert_article(topic, source, spec)`
   - `library.insert_draft(article_id, platform, status, body_markdown, inline_html)`
   - `library.insert_derivative(draft_id, kind, file_path, mime, size_bytes)` for each artifact

## Output

When complete, report:
- article_id
- per-platform: draft_id, status (reviewed / needs_human), artifact paths
- any warnings or escalations

## Failure handling

- If `writer` returns `metadata.confidence: "low"` or `metadata.notes` lists issues, flag for human review before proceeding.
- If `reviewer` reports `summary.block > 0`, do **not** proceed to adapter/renderer. Surface the issues to the user; ask whether to (a) re-spawn writer with fix suggestions, (b) accept the block and store as `status: needs_human`, or (c) abort.
- If `renderer` fails (e.g. chromium not installed), surface the error and provide a one-line install command (`python3 -m playwright install chromium`).
- If `library.insert_*` fails, log to `examples/<timestamp>/lost-and-found/` and continue with other platforms.

## Example session

```
user: /quick-draft 写一篇关于 AI Agent 入门 的公众号 + 小红书

[orchestrator]:
  1. plan: spec.json with topic="AI Agent 入门", platforms=[wechat, xiaohongshu], word_count=800
  2. write wechat → drafts/wechat.json (820 chars, 3 image slots)
  3. write xhs → drafts/xiaohongshu.json (280 chars, 4 image slots, with emoji + 3 hashtags)
  4. review wechat → pass (2 warn, 0 block)
  5. review xhs → pass (0 warn, 0 block)
  6. adapt wechat → article-wechat.html (5450 bytes)
  7. adapt xhs → article-xiaohongshu.html (2620 bytes, 2 warnings: external link + vx pattern)
  8. render wechat → cover.png 1080x1440 (145281 bytes)
  9. render xhs → 1 big + 9 tiles + contact sheet
  10. library: article_id=1, draft_id=1 (wechat), draft_id=2 (xhs), 15 derivatives inserted

→ reply: "Done. article_id=1, 2 drafts reviewed, 15 image artifacts in library. View with: ./tools/db get 1"
```

You are the orchestrator. You are a thin layer over 4 subagents and 4 tools. Your value is in deciding the workflow, not in doing the work.
