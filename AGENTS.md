# self-media-pipeline — Agent 项目指令

## 这是什么

一个 **agent-native plugin**，给公司做自媒体内容生产。给定一段原料（一段主题 / 一篇草稿 / 一个链接），自动生成微信公众号 + 小红书（+ 未来知乎 / B 站）的可发布产物。

**核心不是 HTML 渲染器，是 4 个 subagent 协作的工作流**：
- `writer` 起草内容（用 LLM）
- `reviewer` 审校（事实 + 风格 + 平台硬约束）
- `platform-adapter` 做平台特定适配（公众号清洗 / 小红书 9 宫格）
- `renderer` 渲染（HTML → PNG，9 宫格切图）

**全部产物入 SQLite 内容库**——可追溯、可重放、可改稿。

## 项目结构（plugin 视角）

```
self-media-pipeline/
├── .claude-plugin/plugin.json     # Claude Code 识别
├── hermes-plugin/plugin.yaml      # Hermes 识别
├── AGENTS.md                      # 本文件（给所有 agent 看的项目说明）
├── README.md                      # 给人看的 plugin 介绍
├── skills/                        # 7 个 SKILL.md（领域知识封装）
├── agents/                        # 4 个 subagent 定义（执行主体）
├── commands/                      # 2 个斜杠命令（用户入口）
├── hooks/hooks.json               # sessionStart 钩子
├── tools/                         # 4 个共享 CLI 工具
├── library/                       # L1 内容库（SQLite + MCP server）
├── examples/hello-world/          # 端到端跑通的样例
└── docs/                          # ADR + 贡献文档
```

## 核心设计原则

### 1. SKILL.md 是头等公民
每个 skill 一个目录 + 一份 `SKILL.md`。frontmatter 写元信息（name / description / triggers / allowed-tools / inputs / outputs），body 写领域知识和契约。

### 2. 工具 = 独立可执行
所有工具都是可独立 `shell out` 的 CLI。agent 不需要"理解"工具的实现，只需要知道契约（输入/输出）。

### 3. L1 内容库跟 agent 解耦
`library/data/smp.db` 是普通 CRUD 服务。agent 是用户之一，不是主。L1 通过 MCP 协议暴露给 agent。

### 4. 平台规则三层分
- **硬约束** 进 `constraints.json`（机器可读）
- **风格指南** 在 `SKILL.md` body（创作指引）
- **机械活** 在 `tools/*.py`（清洗/转换/检查）

### 5. 每个 subagent 单一职责
writer 不审校，reviewer 不写作，platform-adapter 不渲染，renderer 不写正文。subagent 之间的契约由 SKILL.md 描述。

## 当前状态（截至 2026-06-02）

| 组件 | 状态 |
|---|---|
| Plugin manifest（双） | ✓ |
| AGENTS.md / README.md | ✓ |
| `skills/` (7) | ✓ 全部就位 |
| `agents/` (4) | ✓ 已写定义（writer/reviewer/renderer/platform-adapter） |
| `commands/` (2) | ✓ quick-draft / library-list |
| `hooks/` | ✓ sessionStart 提示 |
| `tools/` (4) | ✓ list-targets / draft-spec / run-pipeline / db |
| `library/` | ✓ SQLite + MCP server（7 个工具） |
| e2e pipeline | ✓ hello-world 跑通（1 article + 2 drafts + 15 derivatives） |
| 单元测试 | ❌ 0 个 |
| 真实 LLM 起草 | ❌ writer subagent 定义写好但需要真 LLM 接入（用父 agent 的 model: inherit） |

详见 `docs/ADR-001-agent-native-architecture.md`。

## 如何贡献

### 加一个新平台 skill（知乎 / B 站 / 微博）

完整步骤见 `docs/adding-a-new-platform-skill.md`（TL;DR：1-2 天内能完成）。

### 加一个新 subagent

1. 创建 `agents/<name>.md`
2. frontmatter 写 `name` / `description`（含 example block）/ `model: inherit` / `tools: [...]`
3. body 写 system prompt
4. 更新 `hermes-plugin/plugin.yaml` 的 `provides_subagents` 列表
5. 在 README.md 加一行简介

### 加一个新斜杠命令

1. 创建 `commands/<name>.md`
2. frontmatter 写 `description`
3. body 是用户运行该命令时 agent 收到的 prompt
4. 更新 `hermes-plugin/plugin.yaml` 的 `provides_commands` 列表

## 跨 agent runtime 适配

本 plugin 设计支持：
- **Claude Code**：`.claude-plugin/plugin.json` + `agents/*.md` + `commands/*.md`
- **Hermes**：`hermes-plugin/plugin.yaml` + `skills/*/SKILL.md`（subagent 通过 `delegate_task` 工具调度）
- **openclaw**（未来）：plugin 目录结构 + `/subagents` 命令

## 关联

- 起源文档：`~/html-anything/developer_documents/templates-skills-and-marketplace.md`
- 架构决策：`docs/ADR-001-agent-native-architecture.md`
- 新平台贡献指南：`docs/adding-a-new-platform-skill.md`
- 端到端跑通：`examples/hello-world/README.md`
