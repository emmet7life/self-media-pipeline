---
name: library-mcp
description: |
  L1 内容库的 MCP server 描述。把 SQLite 内容库（articles / drafts / derivatives / publish_log）
  暴露成 MCP 工具给 agent 调用。本 skill 描述**工具契约**和**MCP 配置**；实际 server 在
  `library/server.py`。
triggers:
  - self-media-pipeline 的 Step 6（入库）必加载
  - 任何"查询历史内容"、"列历史文章"、"搜主题"的用户输入命中
allowed-tools:
  - mcp_call
inputs:
  - name: operation
    type: enum
    enum: [insert_article, insert_draft, insert_derivative, list_articles, search_articles, get_article, get_draft, list_derivatives, log_publish]
outputs:
  - name: result
    type: object
---

# library-mcp —— 内容库 MCP 工具契约

## 这个 skill 干什么

定义 agent 跟 `library/data/smp.db` 交互的**完整 MCP 工具集**。所有数据最终落 SQLite，agent 只是用户之一。

## 这个 skill 不干什么

- 不实现 SQLite 逻辑（那是 `library/server.py`）
- 不做内容检索/分析的高级特性（先简单 FTS5）
- 不做权限/多用户（第 7+ 周）

## MCP server 启动

```bash
python library/server.py
```

按 stdio MCP 协议暴露以下 tools：

### `library.insert_article`

```json
{
  "name": "library.insert_article",
  "input_schema": {
    "type": "object",
    "properties": {
      "topic": { "type": "string" },
      "source_material": { "type": "string" },
      "style_reference": { "type": "string" }
    },
    "required": ["topic"]
  },
  "output": { "article_id": "<integer>" }
}
```

### `library.insert_draft`

```json
{
  "name": "library.insert_draft",
  "input_schema": {
    "type": "object",
    "properties": {
      "article_id": { "type": "integer" },
      "platform": { "type": "string", "enum": ["wechat", "xiaohongshu"] },
      "status": { "type": "string", "enum": ["draft", "reviewed", "needs_human", "approved"] },
      "body_markdown": { "type": "string" },
      "inline_html": { "type": "string" },
      "metadata_json": { "type": "string" }
    },
    "required": ["article_id", "platform", "status", "body_markdown"]
  },
  "output": { "draft_id": "<integer>" }
}
```

### `library.insert_derivative`

```json
{
  "name": "library.insert_derivative",
  "input_schema": {
    "type": "object",
    "properties": {
      "draft_id": { "type": "integer" },
      "kind": { "type": "string", "enum": ["html_wechat", "png_cover", "png_grid", "preview_html", "source_md"] },
      "file_path": { "type": "string" },
      "mime": { "type": "string" },
      "size_bytes": { "type": "integer" }
    },
    "required": ["draft_id", "kind", "file_path"]
  },
  "output": { "derivative_id": "<integer>" }
}
```

### `library.list_articles`

```json
{
  "name": "library.list_articles",
  "input_schema": {
    "type": "object",
    "properties": {
      "limit": { "type": "integer", "default": 20 },
      "offset": { "type": "integer", "default": 0 },
      "since": { "type": "string", "format": "iso-date", "description": "filter created_at >= since" }
    }
  },
  "output": { "articles": [{ "id", "topic", "created_at" }, ...] }
}
```

### `library.search_articles`

```json
{
  "name": "library.search_articles",
  "input_schema": {
    "type": "object",
    "properties": {
      "query": { "type": "string", "description": "FTS5 query" }
    },
    "required": ["query"]
  },
  "output": { "matches": [{ "id", "topic", "snippet" }, ...] }
}
```

### `library.get_article`

```json
{
  "name": "library.get_article",
  "input_schema": {
    "type": "object",
    "properties": { "article_id": { "type": "integer" } },
    "required": ["article_id"]
  },
  "output": { "id", "topic", "drafts": [...], "derivatives": [...] }
}
```

### `library.log_publish`

```json
{
  "name": "library.log_publish",
  "input_schema": {
    "type": "object",
    "properties": {
      "derivative_id": { "type": "integer" },
      "platform_account": { "type": "string" },
      "publish_url": { "type": "string" },
      "published_at": { "type": "string", "format": "iso-datetime" }
    },
    "required": ["derivative_id", "platform_account"]
  },
  "output": { "publish_log_id": "<integer>" }
}
```

## SQLite schema 位置

`library/schema.sql`（见同目录）

## 关联

- 被 self-media-pipeline 的 Step 6 调用
- 任何人 / 任何 agent 都可以用 `tools/db` CLI 直接查
