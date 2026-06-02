---
name: self-media-pipeline
description: |
  自媒体内容生产 pipeline 顶层工作流。用户在 Hermes TUI 里说"写一篇关于 X 的公众号/小红书"时
  由 orchestrator 加载本 skill。本 skill 定义从原料到可发布产物的端到端步骤、subagent 调度、
  产物在 library/ 的落盘契约、错误恢复策略。本 skill 本身**不直接产出内容**，而是**编排其他
  subagent**（writer / reviewer / platform-adapter / renderer）。
triggers:
  - "写一篇...的公众号/小红书"
  - "把...改写成公众号/小红书版本"
  - "基于...生成一篇内容"
  - "用 self-media-pipeline ..."
allowed-tools:
  - read_file
  - write_file
  - search_files
  - terminal
  - delegate_task    # spawn subagent
inputs:
  - name: topic
    type: string
    required: true
    description: 内容主题或核心问题（一句话）
  - name: target_platforms
    type: list[enum]
    enum: [wechat, xiaohongshu]
    required: false
    default: [wechat, xiaohongshu]
    description: 目标平台；多选时并行起草
  - name: source_material
    type: string
    required: false
    description: 可选原料（链接 / 草稿 / 数据 / 关键词清单）
  - name: style_reference
    type: string
    required: false
    description: 可选风格参考（公司历史文章 ID / 风格描述）
  - name: word_count_target
    type: integer
    required: false
    description: 目标字数（公众号 600-1500；小红书正文不超 1000）
outputs:
  - name: derivative_ids
    type: list[integer]
    description: 写入 library/ 的 derivative 行 id（每个平台一个）
---

# self-media-pipeline

## 这个 skill 干什么

把"用户的自然语言需求"翻译成"多个 subagent 的串并行动作"，最终把**每个目标平台的成品 derivative** 写入 `library/data/smp.db` 的 `derivatives` 表。

## 这个 skill 不干什么

- 不写正文（交给 `writer` subagent）
- 不审校（交给 `reviewer` subagent）
- 不做平台适配（交给 `platform-adapter` subagent）
- 不做 HTML 渲染 / PNG 切片（交给 `renderer` subagent）
- 不入库（统一收口在本 skill 的最后一步）

**原则**：本 skill 只**编排**。所有写操作发生在 subagent session 里，本 skill 只把"成品路径 + 摘要"收上来再调 `library-mcp` 工具入库。

## 工作流（每条对应一个 subagent 调度）

### Step 1 —— 解析与计划

把用户的自然语言解析成一个**机器可读的 spec**，落到 `examples/<timestamp>/spec.yaml`：

```yaml
topic: "<从用户输入提取>"
target_platforms: [<从用户输入提取>]
source_material: <可选>
style_reference: <可选>
word_count_target: <可选>
constraints:        # 平台规则硬性约束
  wechat:
    max_chars: 20000
    inline_css_only: true
  xiaohongshu:
    grid: "3x3"           # 9 宫格
    cover_size: "1080x1440"
```

**判断**：spec 是否能跑通？不能则向用户追问，不要 spawn subagent。

### Step 2 —— 调研（可选）

如果 `source_material` 是 URL 或需要事实核查，调 `fact-check` skill 收集：
- 关键事实清单
- 引用源 URL
- 潜在风险点（敏感词 / 版权 / 时效）

**短路过门**：原料是用户自写、不涉及外部事实 → 跳过。

### Step 3 —— 写作（每个目标平台一个 writer subagent）

对每个 `target_platforms` 中的平台，**并行** spawn `writer` subagent（独立的 Hermes session）。

writer subagent 加载：
- `skills/render-html/SKILL.md`（排版规范）
- `skills/fact-check/SKILL.md`（如果 Step 2 启用）
- 该平台的 skill（如 `skills/platform-wechat/SKILL.md`）

writer 产出的契约（写到 `examples/<timestamp>/drafts/<platform>.md`）：

```yaml
title: <string>
platform: <wechat | xiaohongshu>
body_markdown: <string>      # 原始 markdown
inline_html: <string>        # 已经按平台规则 inline 过的 HTML
images:                       # 配图占位（不需要实际图，但需要位置标注）
  - slot: cover
    aspect: "1080x1440"
    prompt: <string>           # 给 render-image 的生成提示
  - slot: inline-1
    aspect: "16:9"
    prompt: <string>
metadata:
  word_count: <int>
  reading_time_min: <int>
```

**关键**：writer 输出的 HTML 已经是"平台适配过的"——这一步就把 platform-adapter 的活儿干了。如果该平台只有少量规则，可以**让 writer 直接加载 platform skill**，省一个 subagent。

### Step 4 —— 审校（每个 draft 一个 reviewer subagent）

对每个 draft，spawn `reviewer` subagent。reviewer 加载 `skills/fact-check/SKILL.md`，做：
- 事实核查（针对 Step 2 的引用清单）
- 敏感词扫描
- 风格一致性（如果给了 style_reference）
- 字数 / 平台硬性约束自检

reviewer 产出：审校报告（pass / list-of-issues），写到 `examples/<timestamp>/reviews/<platform>.json`。

**审校失败怎么办**：把 issues 回给 writer 让它再写一轮（最多 2 轮），仍不过 → 标注 `status: needs_human` 入库，发通知给用户。

### Step 5 —— 渲染（每个需要图像的产物调一次）

如果产物需要 PNG（小红书必然需要；公众号可选）：

调 `skills/render-image/SKILL.md` 的工具（headless chrome 截图 + 9 宫格切图），把 `draft.images[].prompt` 渲染成实际图片文件。

输出路径：`examples/<timestamp>/renders/<platform>/`。

### Step 6 —— 入库（本 skill 自己干）

调 `skills/library-mcp` 暴露的工具，把以下行写入 SQLite：

```sql
INSERT INTO articles (topic, source_material, style_reference, created_at)
  VALUES (?, ?, ?, ?);

INSERT INTO drafts (article_id, platform, status, body_markdown, inline_html, metadata_json, created_at)
  VALUES (?, ?, 'reviewed', ?, ?, ?, ?);

INSERT INTO derivatives (draft_id, kind, file_path, mime, size_bytes, created_at)
  VALUES (?, ?, ?, ?, ?, ?);
```

最终把 `article_id` 和 `derivative_ids` 作为本 skill 的 output 返回给 orchestrator。

## 错误恢复

| 失败 | 处理 |
|---|---|
| writer subagent 超时（> 5 min） | 取消，回退到更短字数要求再 spawn |
| reviewer 发现 5+ 严重事实问题 | 跳过二次审校，直接 needs_human |
| renderer 截图失败 | 把 `derivative.kind` 留为 `html_only`，提示用户手动重渲 |
| library-mcp 不可达 | 降级：把 derivative 写到 `examples/<timestamp>/lost-and-found/` |

## 不重写

- **平台规则的知识**：全部由对应 platform skill 维护，不在本 skill 里 copy 一份
- **HTML 模板 / CSS 风格**：全部在 `render-html/SKILL.md` 里
- **敏感词词表**：全部在 `fact-check/SKILL.md` 里

本 skill 只**编排**和**入库**。所有领域知识下沉到对应子 skill。

## 关联

- 被加载：orchestrator agent（任何用户输入命中触发词）
- 加载（不直接调工具，但告诉 subagent 加载什么）：
  - `skills/render-html/SKILL.md`
  - `skills/render-image/SKILL.md`
  - `skills/fact-check/SKILL.md`
  - `skills/library-mcp/SKILL.md`
  - `skills/platform-wechat/SKILL.md`
  - `skills/platform-xiaohongshu/SKILL.md`
- 工具契约：见 `tools/run-pipeline` 的 SPEC
