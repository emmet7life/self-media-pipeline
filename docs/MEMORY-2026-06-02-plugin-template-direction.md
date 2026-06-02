# MEMORY-2026-06-02: plugin 方向纠偏、模板库与小红书卡片流程

## 用户原始意图

本项目不是普通内容工具，也不是 markdown 转 HTML 渲染器，而是一个给 **Claude Code / Codex 等本地智能体使用的 agent-native 自媒体内容生成 plugin**。

用户最初让 Hermes 参考 `https://github.com/obra/superpowers.git` 设计插件体系，因为 `superpowers` 的插件结构规范，并且兼容 Claude、Codex、Cursor、OpenCode 等 agent runtime。当前项目暂时只需要优先适配：

- Claude Code
- Codex

用户原计划用 `https://github.com/emmet7life/html-anything.git` 实现需求，但后来发现 `html-anything` 调用本地 agent 的能力受限，不能充分利用本地 agent 的 plugin / skill 体系。不过用户非常认可 `html-anything` 中几十个模板的设计质量，尤其是模板 skill 里的 `example.html`，渲染出来的 HTML 很好看。

## 用户指出的关键问题

### 1. 当前项目缺少模板库能力

当前项目过度依赖 markdown → HTML，这种方式产物单调，不符合真实公众号排版需求。

用户期望本 plugin 也有模板库功能。公众号排版应该是多样的，例如用户给出的公众号文章链接中，排版风格各不相同。这些风格都可以成为模板库中的 `example.html` 示例。

### 2. 需要研究 html-anything 的“好看”原理

需要认真研究 `html-anything`：

- 它如何组织模板 skill
- 它通过什么 prompt 结构让 agent 生成高质量 HTML
- 它如何使用 `example.html`
- 哪些机制可以迁移到当前 agent-native plugin 中

结论：`html-anything` 的模板本质是 prompt composition，不是真正由 agent runtime 自动发现的 skill；但它的 `SKILL.md + example.html` 模板组织方式非常值得迁移。本项目应让 agent 真正读取模板 `SKILL.md` 和 `example.html`，把 example 作为质量锚点。

### 3. 小红书流程原先是错误的

原先把网页截图后直接 3x3 切成 9 张图是不合理的。小红书的图片应该是多张独立可读的发布图，而不是一张大图的碎片。

正确方向：

- 一张图一个 HTML
- 一张图一个 PNG
- 每张图独立成卡片
- contact sheet 只能用于自检，不作为发布图

### 4. MiniMax CLI 应作为可替换 media provider

用户计划使用 MiniMax CLI：

`https://github.com/MiniMax-AI/cli`

用于图片、音频、视频等多媒体生成。但用户不希望当前 plugin 深度耦合 MiniMax，因为后续可能切换其他大模型 CLI。

因此需要抽象出 media provider contract，让 MiniMax 只是一个 provider adapter。

## 本轮已做的修改

### 1. 插件目标改为 Claude Code + Codex

新增：

- `.codex-plugin/plugin.json`

更新：

- `.claude-plugin/plugin.json`
- `README.md`
- `AGENTS.md`
- `CLAUDE.md`

当前主目标 runtime：

- Claude Code
- Codex

Hermes manifest 暂时保留为历史兼容，不再作为当前验收重点。

### 2. 新增模板库骨架

新增 skill：

- `skills/template-library/SKILL.md`

新增模板目录：

- `templates/wechat-magazine-editorial/`
- `templates/xhs-pastel-card-deck/`

每个模板包含：

- `SKILL.md`
- `example.html`

新增工具：

- `tools/list-templates`

模板库原则：

- `example.html` 是质量锚点
- 模板不是皮肤，而是版式、信息密度、组件语言、字体层级和视觉节奏的契约
- 公众号和小红书都不应只靠通用 markdown CSS

### 3. 新增 media provider 抽象

新增：

- `skills/media-provider/SKILL.md`

原则：

- pipeline 只提交标准 JSON 请求
- provider adapter 决定调用 MiniMax CLI 或其他工具
- MiniMax CLI 不散落在 writer / renderer / platform skill 中
- 未来切换其他 CLI 只替换 adapter

### 4. 修正小红书发布图流程

新增：

- `skills/platform-xiaohongshu/tools/build_cards.py`

修改：

- `skills/render-image/tools/render_grid.py`
- `tools/run-pipeline`
- `skills/platform-xiaohongshu/SKILL.md`
- `skills/render-image/SKILL.md`
- `agents/renderer.md`

新流程：

```text
draft JSON
  -> build_cards.py
  -> card-html/01.html ... 09.html
  -> render_grid.py
  -> card-png/01.png ... 09.png
  -> contact-sheet.png only for self-check
```

`slice_grid.py` 保留为低层工具和测试对象，但不再作为小红书发布主流程。

### 5. 记录架构决策

新增：

- `docs/ADR-006-template-library-and-media-provider.md`

该 ADR 记录：

- 为什么从 Hermes 主目标转向 Claude Code + Codex
- 为什么要引入模板库
- 为什么小红书不能切单张大图
- 为什么 MiniMax CLI 必须通过 provider 抽象接入

### 6. 测试与验证

新增测试：

- `tests/test_template_library.py`
- `tests/test_xhs_build_cards.py`

当前测试结果：

```text
python3 tests/run_tests.py
Total: 37 tests, 0 failures, 0 errors
```

实际跑通过：

```bash
./tools/run-pipeline --spec examples/hello-world/spec.json --output-root /tmp/smp-pipeline-output
```

小红书输出已经变为：

```text
xiaohongshu/render/card-html/01.html ... 09.html
xiaohongshu/render/card-png/01.png ... 09.png
xiaohongshu/render/card-png/contact-sheet.png
```

## 后续优化方向

### P0: 公众号模板渲染不要继续依赖通用 markdown renderer

当前已建立模板库骨架，但公众号实际 pipeline 还主要走 `render-html/tools/render.py`。下一步应实现：

- `tools/render-template`
- 或 `skills/render-html` 的模板模式

目标是让公众号 HTML 从 `templates/wechat-*/example.html` 和模板 `SKILL.md` 生成，而不是机械 markdown 转 HTML。

### P0: 真正接入 Claude Code / Codex subagent e2e

当前 writer / reviewer / fact-check 仍有 stub。需要分别验证：

- Claude Code 中 writer subagent 是否能加载 platform skill + template skill
- Codex 中是否能通过 multi-agent 能力执行同等流程
- 两者是否都能正确使用模板库

### P1: 从 html-anything 迁移更多模板思想

不要依赖 `html-anything` runtime，但可以迁移模板思想：

- 每个模板目录一个 `SKILL.md + example.html`
- 公众号：杂志长文、极简商务、案例复盘、深色科技、手账风等
- 小红书：教程卡片、避坑清单、对比表、知识图谱、封面强标题等

迁移时要注意 license 和署名。

### P1: MiniMax provider adapter

基于 `skills/media-provider/SKILL.md` 实现第一个 adapter：

- 输入 provider request JSON
- 调用 MiniMax CLI
- 产出 artifact manifest
- 写入 library derivatives

不要把 MiniMax CLI 调用写死在 `run-pipeline` 或 platform skill 里。

### P1: 小红书卡片生成质量继续提升

当前 `build_cards.py` 是最小可用实现。后续需要：

- 更多模板样式
- 更好的内容拆分
- 每张卡片更强的信息设计
- 图片/插画 slots
- 字体溢出检测
- Playwright 截图 QA

## 注意事项

- `docs/ADR-005-restructure-as-agent-native-plugin.md` 当前有历史换行符 diff，不是本轮逻辑修改重点。
- `slice_grid.py` 仍可保留，但不要再作为小红书发布主流程。
- 模板库应该成为本项目核心能力之一，不是附属装饰。
