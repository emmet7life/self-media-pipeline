---
name: template-library
description: 可复用自媒体视觉模板库。用于公众号文章、小红书卡片、封面图等产物的版式选择；模板以 templates/<id>/SKILL.md + example.html 形式存在。
---

# template-library

## 这个 skill 干什么

为 `writer` / `platform-adapter` / `renderer` 提供可选择的视觉模板。模板不是普通 markdown 主题，也不是 `render-html` 的固定 CSS；它是一个完整的版式参考包：

```text
templates/<template-id>/
├── SKILL.md       # agent 读取的模板契约：适用平台、版式、组件、输出规则
├── example.html   # 手写或精选的高质量目标样例，供 agent 模仿结构与视觉密度
└── example.md     # 可选：示例输入
```

## 设计原则

- **example.html 是质量锚点**：agent 必须模仿它的布局密度、字体层级、组件语言、留白和色彩逻辑，而不是从 markdown 机械转换。
- **模板定义版式池，不定义内容数量**：长内容可以产生更多 section / card；短内容可以少一些，但不能丢信息。
- **平台优先**：公众号模板关注可粘贴 HTML 与长文阅读体验；小红书模板关注每张独立图片的阅读闭环。
- **不绑定 html-anything runtime**：可以学习 html-anything 的模板组织和 prompt 方法，但本项目的模板由本 plugin 的 agent skill 体系消费。

## 使用流程

1. 运行 `./tools/list-templates` 查看可用模板。
2. 按平台和内容类型选择模板，例如：
   - `wechat-magazine-editorial`：公众号杂志长文
   - `xhs-pastel-card-deck`：小红书 3:4 图文卡片组
3. 读取 `templates/<id>/SKILL.md` 和 `example.html`。
4. 生成 HTML 时显式遵守模板契约，必要时复用 example 的 CSS token 和组件结构。

## 输出约束

- 模板产物必须是自包含 HTML。
- 公众号最终进入 `platform-wechat/tools/adapt_html.py` 清洗。
- 小红书必须一张图一个 HTML，一张图一个 PNG；禁止把整页截图切成 9 张发布图。
- 如果模板需要 AI 图片、音频、视频素材，只能通过 `media-provider` skill 的 provider contract 申请，不直接调用 MiniMax 或其他厂商 CLI。

