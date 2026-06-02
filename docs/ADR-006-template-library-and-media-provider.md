# ADR-006: 模板库 + 小红书逐卡片渲染 + 可替换 media provider

**状态**：已接受  
**日期**：2026-06-02  
**范围**：Claude Code / Codex plugin 形态、视觉模板、小红书图片产物、多媒体生成能力

## 背景

本项目目标不是做一个普通 markdown → HTML 转换器，而是做给 Claude Code / Codex 等本地智能体使用的自媒体内容生产 plugin。

早期考虑过基于 `html-anything` 实现，但调研后发现：

- `html-anything` 对本地 agent 的调用是子进程 prompt composition，agent 不真正消费本机 plugin / skill 体系。
- 它的强项是 75 个模板目录：每个模板有 `SKILL.md` + 手写 `example.html`，视觉质量高。
- 它的 `example.html` 原设计主要供 UI 预览，不是 agent few-shot；但本项目可以把 `example.html` 作为 agent-native 模板库的质量锚点。

同时，参考 `superpowers` 后确认：

- Claude Code plugin 需要 `.claude-plugin/plugin.json`。
- Codex plugin 需要 `.codex-plugin/plugin.json`，并显式声明 `"skills": "./skills/"`。
- 技能内容应作为普通 `skills/*/SKILL.md` 分发，不依赖 web runtime。

## 决策

### 1. 当前只把 Claude Code + Codex 作为主目标

保留 `hermes-plugin/plugin.yaml` 作为历史兼容，但当前验收标准改为：

- Claude Code 能识别 `.claude-plugin/plugin.json`
- Codex 能识别 `.codex-plugin/plugin.json`
- 共享 `skills/`、`agents/`、`commands/`、`tools/`

### 2. 新增模板库

模板放在：

```text
templates/<template-id>/
├── SKILL.md
├── example.html
└── example.md optional
```

新增 `skills/template-library/SKILL.md` 和 `tools/list-templates`。

模板不是皮肤，而是视觉与信息结构契约。agent 必须读取模板 `SKILL.md` 和 `example.html`，模仿其布局密度、字体层级、组件语言和留白，而不是只把 markdown 套一层固定 CSS。

当前最小模板：

- `wechat-magazine-editorial`
- `xhs-pastel-card-deck`

### 3. 小红书禁止“单网页截图切 9 张”

原先 `cover-big.png -> slice_grid.py -> 9 tiles` 的思路是错误的。小红书发布图应该是 1-9 张独立可读图片，每张 1080×1440。

新流程：

```text
draft JSON
  -> platform-xiaohongshu/tools/build_cards.py
  -> card-html/01.html ... 09.html
  -> render-image/tools/render_grid.py
  -> card-png/01.png ... 09.png
  -> contact-sheet.png only for self-check
```

`slice_grid.py` 保留为低层工具和测试对象，但不作为小红书发布主流程。

### 4. MiniMax CLI 通过 media-provider 抽象接入

新增 `skills/media-provider/SKILL.md`，定义 provider contract。

pipeline 只提交标准 JSON 请求，不直接调用 MiniMax CLI。后续如果切换其他图片、音频、视频 CLI，只替换 provider adapter，不改 writer/reviewer/platform/renderer 的核心契约。

## 影响

- `run-pipeline` 小红书输出路径变为 `render/card-html/` 和 `render/card-png/`。
- `render_grid.py` 默认单卡尺寸改为 1080×1440。
- README / AGENTS / CLAUDE 状态改为 Claude Code + Codex 优先。
- 文档明确模板库优先于通用 markdown 渲染。

## 后续

- 把更多 `html-anything` 风格的模板迁移为本项目模板，但不要直接依赖其 runtime。
- 设计 `tools/render-template`，让公众号也能从模板 example 生成丰富 HTML，而不是只用 markdown renderer。
- 为 MiniMax CLI 编写第一个 provider adapter，并用 manifest 入库。
