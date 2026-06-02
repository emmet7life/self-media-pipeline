---
name: platform-wechat
description: |
  微信公众号编辑器适配契约。回答"什么样的 HTML / 排版 / 配图 / 字数 才能直接粘贴到微信
  公众号后台"。本 skill 被 writer subagent 在写公众号版本时加载；同时它的 constraints.json
  被 reviewer subagent 在审校时用作硬约束自检。
triggers:
  - "公众号" / "微信" / "wechat" / "wx"
  - 当 spec.yaml 的 target_platforms 含 "wechat" 时自动加载
allowed-tools:
  - read_file
  - write_file
  - terminal
inputs:
  - name: draft
    type: object
    description: writer 产出的 draft 契约（见 self-media-pipeline/SKILL.md Step 3）
outputs:
  - name: adapted_draft
    type: object
    description: 经平台适配后的 draft（HTML 已 inline、敏感词已替换、字数已对齐）
---

# platform-wechat —— 微信公众号适配契约

## 加载时机

1. **writer subagent** 起草公众号版本时**必加载**——把本 skill 当作"平台规则字典"
2. **reviewer subagent** 审校时**必加载**——按 `constraints.json` 逐条自检
3. **不**给 orchestrator 直接加载

## 三层资产

本 skill 目录下有三种资产，各司其职：

```
platform-wechat/
├── SKILL.md            ← 本文件：风格指南 + 工作流（写给 agent 看）
├── constraints.json    ← 硬约束（写给代码/agent 自检，机器可读）
└── tools/
    └── adapt_html.py   ← 实际做 HTML 适配的 CLI 工具
```

**原则**：
- **硬约束进 `constraints.json`**：字号范围、字数上限、必须 inline 的 CSS 属性……这些是事实，agent 不该"自由发挥"
- **风格指南在 SKILL.md body**：语气、结构套路、标题模板、开头钩子……这些是创作指引
- **代码在 `tools/`**：清洗/转换是机械活，写成 CLI 工具让 agent 直接 `shell out`

## 硬约束（来自 constraints.json，agent 必读必遵守）

下面这些**全部**写在 `constraints.json`，本节是给读者预览。**实际值以 JSON 为准**，agent 在审校阶段必须用 `tools/check_constraints.py` 跑一遍。

### 字数 / 结构

- 标题长度：8 - 30 字
- 正文总字数：600 - 5000（推荐 800 - 1500）
- 段落长度：单段不超过 5 行（移动端体验）
- 小标题：每 300-500 字一个
- 配图：每 600-1000 字一张

### 样式（必 inline）

微信公众号编辑器会**清洗掉**：
- `<style>` 标签和外部 CSS
- `class` 选择器（保留标签但 class 名丢失）
- `@media` 查询（移动端适配会被部分剥）
- `position: fixed/sticky`、CSS 变量、Grid 部分高级特性

**必须 inline** 到元素的 `style="..."` 属性：
- `color`, `background-color`, `font-size`, `font-weight`, `line-height`
- `text-align`, `margin`, `padding`
- `border`, `border-radius`
- `max-width`

`tools/adapt_html.py` 的工作就是把上面这些 inline 化、剥掉编辑器不要的属性。

### 图片

- 格式：jpg / png / gif，**不**支持 webp（部分版本）
- 尺寸：推荐宽度 1080px（移动端阅读体验）
- 引用：必须**先上传到微信素材库**才能在文章里用——本 skill **不**实现上传，**留给 `publish` 子工具**
- 占位符约定：HTML 里用 `<img data-wx-src="https://..." data-slot="cover" />` 占位，发布阶段由上传工具替换

### 绝对禁用

- 任何 `<script>` —— 会被 100% 剥
- 任何外部字体引用（`<link>` / `@font-face`）—— 会被剥
- 任何视频 / 音频标签的 `src` —— 必须走腾讯视频 / 微信音频接口

## 风格指南（agent 自由发挥区）

### 标题套路（agent 选 1）

- 数字型：`<数字> + <反差词>`（"7 个被低估的 Python 库"）
- 反问型：`<痛点>？<答案>`（"还在手动部署？自动化才是答案"）
- 身份型：`给 <身份> 的 <内容>`（"给后端工程师的 LLM 入门"）
- 利益型：`<具体收益>`（"用这套 prompt 模板，写作效率翻倍"）

### 开头钩子（前 100 字必抓人）

- 直接抛痛点
- 反常识结论
- 真实案例 / 数字
- 自嘲 / 共情
- **禁**：自我介绍、"在当今..."、铺垫

### 结构

- 推荐 4-6 个小节
- 每节 200-300 字
- 结尾必有"行动召唤"（留言 / 转发 / 点击阅读原文）

### 语气

- 第二人称为主
- 短句多于长句
- 一段一观点，禁大段
- 关键句加粗（`<strong>` 会被保留）

## 工具

### `tools/adapt_html.py`

```bash
python skills/platform-wechat/tools/adapt_html.py < input.html > adapted.html
```

做的事：
1. 内联所有 `<style>` 规则到元素 `style` 属性
2. 剥掉 class 选择器（保留样式但删除 `class="..."`）
3. 替换 `<img data-wx-src="...">` → `<img src="...">`（占位替换）
4. 移除 `<script>` / `<link>` / `<meta>` 危险标签
5. 输出：标准化的"可粘贴 HTML"

**实现位置**：`skills/platform-wechat/tools/adapt_html.py`（**本周必须完成**——这是端到端跑通的最后卡点）

### `tools/check_constraints.py`

```bash
python skills/platform-wechat/tools/check_constraints.py draft.json
```

做的事：
1. 读 `constraints.json` 全部硬约束
2. 对 draft 逐条自检（字数、标题、段落长度、配图密度）
3. 输出 JSON 报告：`{ pass: bool, issues: [{ constraint, severity, location }] }`

**实现位置**：`skills/platform-wechat/tools/check_constraints.py`（**本周必须完成**）

## 关联

- 上游：被 `self-media-pipeline` 的 writer / reviewer subagent 加载
- 下游：调 `render-html` 排版、调 `render-image` 出配图
- 兄弟：`platform-xiaohongshu`（独立，但 schema 对齐方便 pipeline 并行）
