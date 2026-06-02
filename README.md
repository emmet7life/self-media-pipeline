# self-media-pipeline

**An agent-native plugin for self-media content production.**

> 给公司做自媒体内容生产。给定一段原料，自动生成微信公众号 + 小红书（+ 未来知乎 / B 站）的可发布产物。

## 这是什么

一个 **plugin**，不是项目、不是工具集、不是 web 应用。**4 个 subagent 协作 + 7 个 skill + 2 个 command + 1 个 SQLite 内容库**，跑在 Claude Code / Hermes / 其他兼容 agent runtime 上。

## 用户视角：怎么用

在装了此 plugin 的 agent runtime（Claude Code / Hermes / 兼容 runtime）里：

```
/quick-draft 写一篇关于 AI Agent 入门 的公众号 + 小红书
/library-list
```

或者直接用自然语言：

> "用 self-media-pipeline 帮我把这段素材改写成公众号和知乎两个版本"

agent 会自动：
1. 加载 `self-media-pipeline` 顶层 skill
2. spawn `writer` subagent（×2，每个平台一个）
3. spawn `reviewer` subagent
4. spawn `platform-adapter` subagent
5. spawn `renderer` subagent
6. 入 SQLite 内容库

## 安装

**两种模式**：user-level（全局可用，跨项目共享）/ project-level（仅本项目用，仓库自带）

### User-level（推荐，全局可用）

把 plugin 装到 `~/.claude/plugins/` 或 `~/.hermes/plugins/` 下，**所有项目都能用**：

#### Claude Code
```bash
# 方式 1：从 GitHub 装（发布版本）
claude plugin install emmet7life/self-media-pipeline

# 方式 2：从本地 checkout 装（开发中）
git clone https://github.com/emmet7life/self-media-pipeline.git
cd self-media-pipeline
claude plugin install .

# 验证
ls ~/.claude/plugins/self-media-pipeline/
# 应该看到 agents/ commands/ hooks/ skills/ tools/ .claude-plugin/
```

#### Hermes
```bash
hermes plugins install ./self-media-pipeline
```

### Project-level（仓库内自带 / 开发模式）

**适合场景**：
- 你在开发/修改这个 plugin
- 你希望 plugin 跟项目代码一起 version control
- 团队共享：每个开发者 clone 项目就有 plugin

```bash
# 1. 把整个仓库当作 plugin 根 clone
git clone https://github.com/emmet7life/self-media-pipeline.git ~/media-publish-test/
cd ~/media-publish-test/

# 2. 仓库根目录就是 plugin 根，**不要**执行任何 mv / 改名操作
#    - 仓库根已经有：.claude-plugin/ agents/ commands/ hooks/ skills/ tools/
#    - 启动 Claude Code 即可加载
claude --dangerously-skip-permissions
# 3. 验证
ls skills/ agents/ commands/ hooks/  # 都在
```

**常见错误**（**不要**做）：
- ❌ `mv .claude-plugin .claude/` —— Claude Code 期望 `.claude-plugin/` 在 plugin 根，不是 `.claude/`
- ❌ `mv skills/ .claude/skills/` —— plugin 根的内容应直接在根，**不**在 `.claude/` 下
- ❌ 把仓库 clone 到 `~/projects/<name>/` 然后**只 cp 几个目录到 `.claude/`** —— 这会破坏 plugin 完整性

**判断方式**：plugin 根必须有 `.claude-plugin/plugin.json` **和** `skills/` `agents/` `commands/` `hooks/` `tools/` 平级。

## 架构（一图流）

```
┌──────────────────────────────────────────────────────┐
│ L1  library/ —— 持久化资产层（普通服务，跟 agent 解耦）│
│     SQLite + FTS5 (articles / drafts / derivatives)  │
│     MCP server 暴露 CRUD + 搜索给 agent              │
└──────────────────────────────────────────────────────┘
        ↑  MCP（stdio）
┌──────────────────────────────────────────────────────┐
│ L2  Hermes / Claude Code orchestrator                │
│     - 加载 self-media-pipeline skill                 │
│     - 调度 4 个 subagent（delegate_task / Task tool） │
│     - subagent: writer / reviewer / renderer /       │
│       platform-adapter                                │
└──────────────────────────────────────────────────────┘
        ↑  tool calls
┌──────────────────────────────────────────────────────┐
│ L3  skills/ —— 原子能力                              │
│   self-media-pipeline/   顶层 orchestrator skill      │
│   platform-wechat/       公众号编辑器规则 + 适配工具  │
│   platform-xiaohongshu/  小红书 9 宫格 + 封面工具     │
│   render-html/           HTML 排版（inline CSS）      │
│   render-image/          HTML → PNG（headless chrome）│
│   fact-check/            引用核查 / 敏感词 / 版权     │
│   library-mcp/           内容库 MCP 工具契约          │
└──────────────────────────────────────────────────────┘
        ↑  shell out
┌──────────────────────────────────────────────────────┐
│ tools/ —— 跨 skill 共享的 CLI                         │
│   list-targets           列出所有平台目标 + 适配状态  │
│   draft-spec             生成平台目标 spec            │
│   run-pipeline           手动触发端到端 pipeline      │
│   db                     library SQLite 的 CLI 包装  │
└──────────────────────────────────────────────────────┘
```

## plugin 目录

```
self-media-pipeline/
├── .claude-plugin/plugin.json     # Claude Code manifest
├── hermes-plugin/plugin.yaml      # Hermes manifest
├── AGENTS.md / CLAUDE.md          # 项目级指令（多 runtime 适配）
├── README.md                      # 本文件
├── skills/                        # 7 个 SKILL.md（领域知识）
├── agents/                        # 4 个 subagent 定义
├── commands/                      # 2 个斜杠命令
├── hooks/hooks.json               # sessionStart 提示
├── tools/                         # 4 个共享 CLI
├── library/                       # L1 内容库
│   ├── schema.sql
│   ├── server.py                  # MCP server
│   └── data/smp.db                # SQLite（gitignored）
├── examples/hello-world/          # 端到端跑通样例
└── docs/                          # ADR + 贡献文档
    ├── ADR-001-agent-native-architecture.md
    └── adding-a-new-platform-skill.md
```

## 第一次跑通

```bash
cd ~/self-media-pipeline
sqlite3 library/data/smp.db < library/schema.sql
./tools/draft-spec --topic "AI Agent 入门" --platforms wechat,xiaohongshu --out examples/hello-world/spec.json
./tools/run-pipeline --spec examples/hello-world/spec.json
./tools/db get 1
```

详见 [`examples/hello-world/README.md`](examples/hello-world/README.md)。

## 设计原则

1. **SKILL.md 是头等公民** —— 每个 skill 一个目录 + 一份 SKILL.md，frontmatter 写元信息，body 写知识 + 契约。
2. **工具 = 独立可执行** —— agent 调工具就是 `shell out`，工具可以单独测试。
3. **L1 内容库跟 agent 解耦** —— agent 是用户，不是主。L1 是普通 CRUD 服务。
4. **平台规则三层分** —— 硬约束进 `constraints.json`、风格指南在 SKILL.md body、机械活在 `tools/*.py`。
5. **每个 subagent 单一职责** —— writer 不审校，reviewer 不写作，platform-adapter 不渲染，renderer 不写正文。
6. **plugin 跨 runtime 兼容** —— 双 manifest（`.claude-plugin/plugin.json` + `hermes-plugin/plugin.yaml`），共享 `skills/` / `agents/` / `commands/` / `hooks/`。

## 贡献

- **加新平台 skill**（知乎 / B 站 / 微博）：见 [`docs/adding-a-new-platform-skill.md`](docs/adding-a-new-platform-skill.md)，1-2 天能完成
- **加新 subagent**：创建 `agents/<name>.md`，更新 `hermes-plugin/plugin.yaml`
- **加新 command**：创建 `commands/<name>.md`，更新 `hermes-plugin/plugin.yaml`
- **架构决策**：[`docs/ADR-001-agent-native-architecture.md`](docs/ADR-001-agent-native-architecture.md)

## 当前状态

| 组件 | 状态 |
|---|---|
| Plugin manifest（双） | ✓ |
| `skills/` (7) | ✓ |
| `agents/` (4) | ✓ |
| `commands/` (2) | ✓ |
| `hooks/` | ✓ |
| `tools/` (4) | ✓ |
| `library/` (SQLite + MCP) | ✓ |
| e2e 端到端（hello-world） | ✓ |
| 单元测试 | ❌ 0 个 |
| 真实 LLM 起草（writer subagent 用 `model: inherit`） | ❌ 待 e2e 验证 |
| 微信 API 直接发布 | ❌ 第 9+ 周 |
| GUI / web 入口 | ❌ 第 9+ 周 |

## 关联

- 起源 / 上下文：`~/html-anything/developer_documents/templates-skills-and-marketplace.md`
- 架构决策：`docs/ADR-001-agent-native-architecture.md`
- 新平台贡献指南：`docs/adding-a-new-platform-skill.md`
- 端到端跑通样例：`examples/hello-world/README.md`
