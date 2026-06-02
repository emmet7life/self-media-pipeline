---
description: "List articles / drafts / derivatives in the L1 content library. Wraps the `tools/db` CLI. Useful for browsing what the self-media-pipeline has produced so far."
---

# /library-list

## What it does

Show the L1 content library (`library/data/smp.db`) contents. Wraps the `tools/db` CLI so the user doesn't have to remember its syntax.

## Usage

```
/library-list                          # list all articles (default)
/library-list articles                 # same as above
/library-list drafts --article-id=1   # drafts for article 1
/library-list derivatives --article-id=1  # all PNG/HTML artifacts for article 1
/library-list search "AI Agent"        # FTS5 full-text search
/library-list stats                    # counts per table
```

## Subcommands

- `articles` (default): list articles with id, created_at, topic
- `drafts`: list drafts (filter by `--article-id`)
- `derivatives`: list artifacts (filter by `--article-id` or `--draft-id`)
- `search <query>`: FTS5 search across articles + drafts
- `stats`: row counts per table

## How it works

This command is a thin wrapper. It calls:

```bash
# Default: list articles
./tools/db list-articles --limit 20

# Drafts / derivatives
./tools/db list-drafts --article-id <article_id>
./tools/db list-derivatives --article-id <article_id>
./tools/db list-derivatives --draft-id <draft_id>

# Articles for a specific id (with drafts + derivatives)
./tools/db get <article_id>

# Full-text search
./tools/db search "<query>"

# Stats
./tools/db stats

# Explicit initialization is available, but normal commands auto-initialize too
./tools/db init
```

## Output formatting

Format the raw CLI output for the user:
- For `articles`: a Markdown table with id, created_at, topic
- For `get <id>`: a hierarchical view: Article → Drafts (per platform) → Derivatives (per kind)
- For `search`: a list of matches with snippet preview
- For `stats`: 4 lines of counts (articles / drafts / derivatives / publish_log)

## Example session

```
user: /library-list

[orchestrator]:
  → run: ./tools/db list-articles --limit 20
  → format as table

  ID    CREATED              TOPIC
  ---------------------------------------------------------------
  1     2026-06-02 08:20:19  AI Agent 入门

  1 article in library.
```

```
user: /library-list get 1

[orchestrator]:
  → run: ./tools/db get 1

  Article #1: AI Agent 入门
    created_at: 2026-06-02 08:20:19
    source_material: https://lilianweng.github.io/posts/2023-06-23-agent/
    drafts (2):
      [1] wechat       status=reviewed   title=AI Agent 入门：3 步搭建你的第一个智能体
      [2] xiaohongshu  status=reviewed   title=AI Agent 入门🌟 3 步上手！
    derivatives (15):
      [1] preview_html: .../wechat/article.html
      [2] adapted_html: .../wechat/article-wechat.html
      [3] png_cover:    .../wechat/render/cover.png
      [4] preview_html: .../xiaohongshu/article.html
      [5] adapted_html: .../xiaohongshu/article-xiaohongshu.html
      [6] png_cover:    .../xiaohongshu/render/card-png/01.png
      [7-15] png_grid:  .../xiaohongshu/render/card-png/01-09.png
```

You are a librarian. Surface the data; don't transform it.
