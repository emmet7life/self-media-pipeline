---
name: platform-xiaohongshu
description: 小红书笔记适配契约。回答"什么样的图片矩阵 + 标题 + 正文 才能直接发布到小红书 App"。 本 skill 被 writer subagent 在写小红书版本时加载；同时它的 constraints.json 被 reviewer subagent 在审校时用作硬约束自检。
---

# platform-xiaohongshu —— 小红书笔记适配契约

## 加载时机

1. **writer subagent** 起草小红书版本时**必加载**
2. **renderer subagent** 渲染 9 宫格时**必加载**（决定切图参数）
3. **reviewer subagent** 审校时**必加载**——按 `constraints.json` 自检

## 三层资产

```
platform-xiaohongshu/
├── SKILL.md
├── constraints.json
└── tools/
    ├── adapt_html.py        # 预览 HTML 清洗
    ├── build_cards.py       # draft → 每张独立小红书卡片 HTML
    ├── check_constraints.py # 硬约束自检
    └── slice_grid.py        # 低层切图工具；不作为发布主流程
```

## 硬约束（来自 constraints.json）

### 标题

- 长度：6 - 20 字（**严格**，超 20 字会被截断显示）
- **必须含 emoji 或符号**（小红书"种草感"的来源之一）
- 关键词前置（前 8 字最关键，决定搜索曝光）

### 正文

- 长度：100 - 1000 字（**严格上限 1000**，超出会折叠）
- 分段：每段不超过 3 行
- **必须含话题标签**：`# <话题>` 至少 3 个，放正文末尾
- 关键词密度：核心关键词出现 2-3 次

### 配图（核心）

**小红书的发布形态 = 1 张封面 + 最多 9 张正文图**：

- 封面图：1080 × 1440 px（3:4 竖版），≤ 5 MB
- 正文图：每张 1080 × 1440 px（统一比例）
- 数量：1 - 9 张（推荐 4-6 张，过少显得没内容，过多刷不完整会被降权）
- 格式：jpg / png（**不**支持 webp）
- 文件大小：单张 ≤ 5 MB

### 多图卡片（核心约束）

小红书发布图必须是**独立 1-9 张 1080 × 1440 图片**。禁止把一个网页截图或一张大图切成 9 张发布图。

正确流程：
1. `tools/build_cards.py`：把 draft 拆成 `card-html/01.html` ... `09.html`
2. `render-image/tools/render_grid.py`：逐个 HTML 截图成 `card-png/01.png` ... `09.png`
3. `contact-sheet.png` 只作为自检预览，不发布

### 绝对禁用

- 任何外链（`http://` / `https://`）——会被折叠
- 任何二维码 / 微信号 ——平台风控
- 政治 / 医疗 / 金融无资质话题
- 标题党词（"震惊！"、"99% 的人不知道"）——限流

## 风格指南（agent 自由发挥区）

### 标题模板（小红书"流量标题"）

- 数字 + 痛点：`<数字> 个 <痛点>，<反常识解决方案>`
- 收藏型：`建议收藏！<内容>`
- 教程型：`<身份> 必看！<具体教程>`
- 对比型：`<A> vs <B>，<结论>`
- 必备：emoji 1-3 个

### 正文结构（"种草感"骨架）

1. **钩子**（前 30 字）：点出场景 / 痛点 / 反常识
2. **主体**（2-4 段）：干货 / 步骤 / 对比
3. **互动召唤**：评论关键词 / 求分享 / 关注
4. **话题标签**：3-5 个 `#` 标签

### 语气

- 第一人称、闺蜜聊天风
- 短句 + emoji 节奏
- **禁**：说教感、广告感、学术腔

### 配图风格

- 封面：醒目标题 + 主视觉 + 配色统一
- 正文图：步骤图 / 对比图 / 数字图 / 截图
- 风格统一：同一调色板、同一字体、同一布局语言
- **禁**：白底大字、纯文字图

## 工具

### `tools/adapt_html.py`

同公众号模式（小红书图片外嵌 HTML 也要 inline CSS）。但额外要做的：
- 把 `<img data-xhs-src="..." data-slot="..." />` 标位
- 不输出可粘贴 HTML，**只输出预览 HTML**（小红书发布不接收 HTML）

### `tools/check_constraints.py`

自检项：
- 标题长度、emoji 数
- 正文长度
- 话题标签数
- 配图数量（1-9）
- 配图尺寸（每张必须 1080×1440）

### `tools/build_cards.py`（核心）

```bash
python skills/platform-xiaohongshu/tools/build_cards.py \
    --draft examples/<run-id>/drafts/xiaohongshu.json \
    --output-dir examples/<run-id>/render/xiaohongshu/card-html \
    --count 9
```

输出：
- `card-html/01.html` ... `card-html/09.html`（每个文件是一张 1080×1440 发布图的源 HTML）
- `manifest.json`

### `tools/slice_grid.py`（兼容/低层工具）

仅用于特殊场景或测试，不作为小红书发布图主路径。发布主路径必须走 `build_cards.py` + `render_grid.py`。

## 关联

- 上游：被 `self-media-pipeline` 的 writer / reviewer / renderer 加载
- 下游：调 `render-image` 出主视觉图、调 `render-html` 出预览 HTML
- 兄弟：`platform-wechat`（独立，schema 对齐）
