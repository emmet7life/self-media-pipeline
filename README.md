# self-media-pipeline

公司自媒体内容生产平台。纯 agent-native 架构。零 web 框架，零 Next.js，零 IndexedDB。

## 这个项目是什么

一个**由本地 agent 编排**的自媒体内容生产工作流。

输入：一段原料（话题 / 草稿 / 链接 / 数据）。
输出：针对目标平台（微信公众号、小红书……）可直接发布的成品。

中间所有步骤——调研、写作、审校、平台适配、渲染、切片、入库——全部由**本地 agent subagent** 完成，每个 subagent 加载自己的 `SKILL.md`、调用自己的工具链。

## 这个项目不是什么

- **不是** web 应用。**没有**浏览器入口、**没有** GUI、**没有** Next.js、**没有** IndexedDB。
- **不是** 内容生成 LLM。**不**提供模型；模型由 agent runtime（Hermes）选择。
- **不是** 平台 SDK 包装。**不**绑定某个 SaaS、**不**依赖第三方 API 才能运行。
- **不是** html-anything 的 fork / 二开。`~/html-anything` 与本项目**完全独立**。

## 用户交互的唯一入口

Hermes TUI / Hermes CLI / 任何 Hermes MCP 客户端。

用户说一句话，orchestrator agent 决定调哪些 subagent、走哪些 skill、最终把成品写到 `library/` 的 SQLite 里。

## 架构（三层）

```
┌────────────────────────────────────────────────────────────┐
│ L1  library/ —— 持久化资产层（普通服务，跟 agent 解耦）     │
│   - SQLite + FTS5（articles / derivatives / publish_log）  │
│   - MCP server 暴露 CRUD + 搜索给 agent                    │
│   - 可被人用 SQL/CLI 直查、可被 agent 用 MCP 调用           │
└────────────────────────────────────────────────────────────┘
        ↑  MCP（stdio）
┌────────────────────────────────────────────────────────────┐
│ L2  Hermes orchestrator session —— 用户唯一入口             │
│   - 用户用自然语言给任务                                    │
│   - orchestrator 解析意图、规划子任务、调度 subagent         │
│   - 关键 subagent（按需 spawn，session 隔离）：              │
│       • writer            写作                              │
│       • reviewer          审校（事实 / 风格 / 敏感词）       │
│       • platform-adapter  平台适配                          │
│       • renderer          渲染（HTML / PNG）                │
│   - 每个 subagent 加载自己领域的 SKILL.md                    │
└────────────────────────────────────────────────────────────┘
        ↑  tool calls
┌────────────────────────────────────────────────────────────┐
│ L3  skills/ —— 原子能力（每个一个目录，自包含）             │
│   self-media-pipeline/   顶层工作流（被 orchestrator 加载） │
│   platform-wechat/       公众号编辑器规则 + 适配工具         │
│   platform-xiaohongshu/  小红书 9 宫格 + 封面工具            │
│   render-html/           HTML 排版（内联 CSS / 响应式）      │
│   render-image/          HTML → PNG（headless chrome）      │
│   fact-check/            引用核查 / 敏感词 / 版权           │
│   library-mcp/           内容库 MCP server 描述             │
└────────────────────────────────────────────────────────────┘
        ↑  shell out
┌────────────────────────────────────────────────────────────┐
│ tools/ —— 跨 skill 共享的 CLI 工具（独立可执行）            │
│   list-targets           列出所有平台目标 + 适配状态         │
│   draft-spec             生成平台目标 spec（机器可读）       │
│   run-pipeline           手动触发一次端到端 pipeline        │
│   db                     library SQLite 的 CLI 包装         │
└────────────────────────────────────────────────────────────┘
```

## 目录速查

```
self-media-pipeline/
├── README.md                  ← 本文档
├── skills/                    ← L3 原子 skill（每个一个目录）
│   ├── self-media-pipeline/   ← 顶层工作流（orchestrator 加载）
│   ├── platform-wechat/
│   ├── platform-xiaohongshu/
│   ├── render-html/
│   ├── render-image/
│   ├── fact-check/
│   └── library-mcp/
├── tools/                     ← L3 共享 CLI 工具
├── library/                   ← L1 持久化
│   ├── schema.sql
│   ├── server.py              ← MCP server 骨架
│   └── data/                  ← SQLite 文件（gitignore）
├── examples/                  ← 跑通的端到端样例
└── docs/                      ← 架构决策记录（ADR）
```

## 第一次跑通

详见 `examples/hello-world/`。

最短路径：

```bash
# 1. 准备 library
sqlite3 library/data/smp.db < library/schema.sql

# 2. 让 Hermes 加载 orchestrator skill
hermes skill load skills/self-media-pipeline

# 3. 在 Hermes 里说一句话
# "用 self-media-pipeline 写一篇关于 [话题] 的公众号文章，标题自拟，800 字左右。"
```

## 设计原则

1. **SKILL.md 是头等公民**。每个 skill 一个目录，一份 `SKILL.md` 是它的 manifest + 行为契约。
2. **工具 = 独立可执行**。skill 调工具就是 `shell out`，工具可以单独测试。
3. **L1 内容库跟 agent 完全解耦**。agent 是用户，不是主。Library 是普通 CRUD 服务。
4. **平台规则 = 知识，写在 SKILL.md body 里**。不是写死的 TypeScript 函数。
5. **每个 subagent 单一职责**。writer 不审校，reviewer 不写作，platform-adapter 不渲染。
6. **commit message 写为什么，不写做了什么**。git log = 决策历史。

## 路线图

- **第 1-2 周**（现在）：骨架 + 顶层 pipeline + 两个平台 skill（公众号、小红书） + 四个原子 skill + L1 库 schema
- **第 3-4 周**：renderer 工具实现（HTML→PNG、9 宫格切图）+ end-to-end 跑通一次公众号
- **第 5-6 周**：end-to-end 跑通一次小红书 + L1 内容库 MCP 化
- **第 7-8 周**：事实核查 skill 工具实现 + 协作（多账号 / 多用户）
- **第 9+ 周**：评估接入公司 OA / 飞书 / 企微通知

详细路线见 `docs/ADR-001-agent-native-architecture.md`。
