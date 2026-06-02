# ADR-001: agent-native 架构 + 路径 A（小团队 1-3 人）

**状态**：已接受
**日期**：2026-06-02
**作者**：项目 owner
**范围**：项目顶层架构决策

---

## 背景

公司需要一个**自媒体内容生产平台**：输入原料 → 一键产出微信公众号（HTML 可粘贴）、小红书（图片矩阵）、其他平台适配版。

可选项：
1. 二次开发开源项目 `~/html-anything`（详见 `~/html-anything/developer_documents/templates-skills-and-marketplace.md`）
2. 自建一个**纯 agent-native** 系统，不依赖任何 web 框架

需要在这个早期做选择。

## 决策

**选择 2：自建纯 agent-native 系统，路径 A（小团队 1-3 人，先做出来）。**

- 仓库位置：`~/self-media-pipeline`（独立仓库，**完全脱离** `~/html-anything`）
- 主 agent runtime：**Hermes**（已在用；有 TUI、subagent、delegate_task）
- 第 1-2 周范围：**公众号 + 小红书** 双平台并行起草
- 内容库：**SQLite + FTS5**（无需先上 Postgres）
- 前端：先**无**（用 Hermes TUI 交互），等第 9+ 周评估是否需要 web 入口

## 决策的"为什么"

### 为什么不二次开发 html-anything

| 维度 | html-anything | 纯 agent-native |
|---|---|---|
| **skill 体系** | 项目 `next/src/lib/templates/skills/` 是 prompt 包，不是真 agent skill——本地 agent `~/.codex/skills/` 不被消费 | 真·agent skill，runtime 自动发现 |
| **agent 调用方式** | `spawn(bin, --message)` 单次 shell 调用 | 长会话 + subagent + 工具循环 |
| **协作** | 单人单浏览器（IndexedDB 持久化） | 内容库可多人多端共享 |
| **平台扩展** | 改 TypeScript + rebuild + 重新部署 | 改 SKILL.md + 调工具 |
| **产品形态** | 单页浏览器工具 | 工作流编排（更接近"团队内容平台"的真实需求） |
| **架构约束** | Next.js 16 / Turbopack / AGENTS.md 强约束 | 自由 |

**最关键**：html-anything 的"产品形态"（单页浏览器工具）跟我们目标"产品形态"（团队内容平台）**根本不匹配**。硬套会让产品难用，迟早要拆。

### 为什么是路径 A（小团队 1-3 人）不是路径 B（先有 html-anything 兜底）

- 团队规模 1-3 人，6 个月内跑通给老板演示
- 路径 A 没有"迁移债务"——一开始就走对的路
- 路径 B 的"先把 html-anything 跑起来再迁"会引入两套概念，后期清理成本高
- 如果后期要 GUI，路径 A 的 L1 内容库已经服务化了，加 React/Vue 前端就是"另一个客户端"，不是迁移

### 为什么是 Hermes 不是其他 agent

- 已经在用，团队熟悉
- TUI 体验稳定
- `delegate_task` / subagent 机制成熟
- `~/.hermes/skills/` 自动发现 SKILL.md，跟本项目设计天然契合
- 风险：Hermes 还年轻，跨平台稳定性需要观察。**缓解**：所有 SKILL.md 是纯文本 + frontmatter，必要时可移植到 Codex / Claude Code

### 为什么 SQLite 不是 Postgres

- 团队规模小，初期并发 < 5
- 全文搜索 FTS5 已够用（足够覆盖 10w 篇内容）
- 零部署成本（一个文件）
- 升级路径：`sqlite3 ... .dump | psql` 即可迁到 Postgres
- 风险：写并发差。**缓解**：WAL 模式（已在 schema.sql 启用）；所有写都通过 MCP server 串行

## 决策的代价

- **短期**：从零写，不能"先 demo 一下"——前 2 周只有骨架
- **学习成本**：团队需要熟悉 SKILL.md frontmatter、Hermes subagent、MCP 协议
- **没有现成 UI**：用户必须用终端 / IDE
- **没有现成"平台规则数据库"**：要自己整理（公众号清洗规则、小红书算法偏好等）

## 决策的可逆性

**部分可逆**：
- ✅ L1 内容库设计是合理的（articles / drafts / derivatives / publish_log + FTS5），即使换 stack 也保留
- ✅ 平台 skill 是 SKILL.md（纯文本 + 工具描述），换 agent runtime 也能用
- ❌ writer / reviewer / renderer 的 subagent 划分绑定了 Hermes 的 subagent 抽象；换 agent runtime 需要重写工作流

**不可逆**：
- 已写好的几百行 SQL schema、Python server 是一次性投入
- 团队对 SKILL.md frontmatter 约定的熟悉度，是"沉没成本"也是"护城河"

## 后续动作

- [x] 仓库初始化 + 骨架
- [x] self-media-pipeline 顶层 SKILL.md
- [x] platform-wechat / platform-xiaohongshu / 4 个原子 skill 的 SKILL.md
- [x] L1 内容库 schema + MCP server 骨架
- [x] tools/ CLI 骨架
- [x] examples/hello-world 跑通骨架版
- [ ] **第 3 周**：render-html/render-image/平台 adapt 工具实现，end-to-end 跑通公众号
- [ ] **第 5 周**：end-to-end 跑通小红书 9 宫格
- [ ] **第 7 周**：fact-check 工具实现 + 多用户雏形
- [ ] **第 9+ 周**：评估 GUI / 接入 OA / 飞书

## 备选方案（保留决策历史）

### 备选 A1：二次开发 html-anything

详见 `~/html-anything/developer_documents/templates-skills-and-marketplace.md` 的"档 1-4 路线建议"。

**为什么没选**：产品形态错配 + skill 体系不可用 + 长期受 Next.js 约束。

### 备选 A2：路径 B（先有 html-anything 兜底，逐步迁移）

**为什么没选**：迁移债务重。团队规模小，宁愿一开始就走对。

### 备选 A3：自建但用 web 框架（Next.js / FastAPI 等）

**为什么没选**：过早。GUI 不是核心价值。Hermes TUI 已经够用。等用户量起来再加 GUI。

## 关联

- 项目根：`/home/cjl/self-media-pipeline/`
- 起源文档：`/home/cjl/html-anything/developer_documents/templates-skills-and-marketplace.md`
