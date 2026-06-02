---
name: render-html
description: |
  通用 HTML 排版规范。提供"单文件、可邮件发送、可粘贴到公众号编辑器"的 HTML 输出能力。
  本 skill 写"排版的为什么"（设计原则、可读性约束），不写"具体 HTML 怎么写"——后者由
  platform-* skill 决定。
triggers:
  - writer subagent 写完原始 markdown 后必加载
  - platform-adapter subagent 做最终 HTML 时必加载
allowed-tools:
  - read_file
  - write_file
  - terminal
---

# render-html —— 通用 HTML 排版规范

## 这个 skill 干什么

回答"**一段内容应该长成什么 HTML 形态**"——字号、配色、间距、栅格、标题层级、列表/引用/图片/代码块等通用排版元素。

## 这个 skill 不干什么

- 不写平台特定规则（公众号清洗 CSS、小红书图片矩阵）——那些在 `platform-*` skill
- 不调渲染工具（HTML→PNG）——那是 `render-image`
- 不改用户原文——只排版不改字

## 输出契约

writer 调用本 skill 后，产出的 HTML 必须满足：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{title}}</title>
</head>
<body>
  <article class="smp-article">
    <h1>{{title}}</h1>
    {{body}}
  </article>
</body>
</html>
```

其中 `{{body}}` 是排版好的内容，**所有 CSS 都在内联**（虽然本 skill 不强调平台清洗，但 inline 是默认——一旦某个平台要清洗就免去二次处理）。

## 设计原则

### 1. 移动优先

- 基准宽度 375px（iPhone SE）
- 字号基准 16px（中文）/ 14px（英文）
- 行高 1.6 - 1.8（移动端阅读）
- 段落间距 ≥ 1.5em

### 2. 视觉层级

- 标题字号：H1 = 1.875em, H2 = 1.5em, H3 = 1.25em, H4 = 1.125em
- 标题字重：600-700
- 标题与正文间距：上下 1em
- 强调：用 `<strong>` 不用 `<b>`，用 `<em>` 不用 `<i>`

### 3. 配色

- 正文：#333（不全黑）
- 链接：#0066cc
- 强调背景：#fff5e6
- 引用块：左边框 4px solid #ddd，背景 #f9f9f9
- 禁用：纯黑 + 纯白对比

### 4. 排版元素

| 元素 | 排版规则 |
|---|---|
| 段落 | 段间空一行，段首不缩进 |
| 列表 | 无序用 `•`，有序用 `1. 2. 3.`；嵌套不超过 3 层 |
| 引用 | 用 `<blockquote>`，左边框 + 浅灰背景 |
| 代码 | 行内 `<code>` 浅灰背景；代码块用 `<pre>` 暗色背景 |
| 图片 | 必须有 `alt`；居中；caption 用 `<figcaption>` |
| 表格 | 边框 1px，斑马纹可选；移动端建议改列表 |

### 5. 不要做的事

- 不要用 `<style>` 块（inline 友好原则）
- 不要用 CSS 变量（兼容性差）
- 不要用 Grid 复杂布局（移动端渲染不一致）
- 不要引入外部字体（必被剥）
- 不要动画 / transition（公众号会剥）

## 工具

### `tools/render.py`（**第 3 周实现**）

```bash
python skills/render-html/tools/render.py --input draft.md --output article.html
```

做的事：
- markdown → HTML（用 `markdown-it-py`）
- 应用上面的排版规则（template）
- 内联所有 CSS
- 输出可粘贴的单文件 HTML

## 关联

- 上游：被 writer subagent 加载
- 下游：被 platform-* skill 进一步适配
- 兄弟：`render-image`（HTML→PNG）
