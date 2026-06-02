# 如何新增一个平台 skill（知乎 / B 站 / 头条 / 微博……）

本文档写给"接下来要加知乎 skill"的人。

读完你将能：在 1-2 天内给 self-media-pipeline 加一个新平台（写代码 0.5 天 + 写 SKILL.md 0.5 天 + 跑通 e2e 0.5 天）。

## TL;DR 流程

```
1. 复制最近的 skill 模板（推荐 platform-xiaohongshu，比 platform-wechat 简单）
2. 改目录名 / 改 SKILL.md frontmatter / 改 body 里的风格指南
3. 改 constraints.json 的硬约束值（字数、尺寸、禁用词……）
4. 实现 tools/adapt_html.py（平台特定清洗）
5. 实现 tools/check_constraints.py（基本是复制改约束引用）
6. tools/list-targets 加上新平台元数据
7. 跑一遍 examples/hello-world 验证（如果用新平台就改 spec）
8. commit
```

## 详细步骤

### Step 1：选模板

| 平台类型 | 推荐模板 | 原因 |
|---|---|---|
| 接受 HTML 粘贴（公众号、知乎、Notion） | `platform-wechat` | 都有"清洗 HTML" 的需求 |
| 发布形态是图片矩阵（小红书、Instagram、绿洲） | `platform-xiaohongshu` | 都有"切 9 宫格"的需求 |
| 发布形态是纯文本 + 链接（Twitter、微博、Bluesky） | **没有现成模板**——直接新建空目录 | 行为模式更简单，不需要图片工具 |

```bash
# 例子：加知乎
cp -r skills/platform-wechat skills/platform-zhihu
cd skills/platform-zhihu
rm tools/adapt_html.py tools/check_constraints.py   # 重新实现
```

### Step 2：改 `SKILL.md`

**frontmatter** 必改字段：

```yaml
---
name: platform-zhihu                    # 改：目录名
description: |                          # 改：触发词 + 一句话定位
  知乎答案/文章适配契约。回答"什么样的 HTML / 排版 / 配图 / 字数
  才能直接发布到知乎"。
triggers:
  - "知乎" / "zhihu" / "乎"
allowed-tools: [...]                     # 平台特定工具
inputs/outputs:                          # 跟 platform-wechat 一样
  ...
---
```

**body** 改 4 个部分：
1. **加载时机**：本平台有没有 `renderer` 步骤？（知乎不需要 9 宫格，所以"渲染"步骤可省）
2. **硬约束**：见 Step 3
3. **风格指南**：把 platform-wechat 的"标题套路 / 开头钩子 / 结构"全部改写成知乎风格
4. **工具**：列 `tools/adapt_html.py` 和 `tools/check_constraints.py` 的存在和用法

### Step 3：改 `constraints.json`

知乎的硬约束（参考实际填写）：

```json
{
  "version": 1,
  "platform": "zhihu",
  "word_count": {
    "title_min": 5,
    "title_max": 50,        // 知乎允许较长标题
    "body_min": 300,
    "body_max": 50000,      // 知乎支持长文
    "body_recommended_min": 800,
    "body_recommended_max": 5000,
    "paragraph_max_lines": 8
  },
  "css_must_inline": [...],     // 跟公众号几乎一样
  "css_will_be_stripped": [...],
  "tags_forbidden": ["script", "link[rel=stylesheet]"],
  "image": {
    "format_supported": ["jpg", "png", "gif", "webp"],   // 知乎支持 webp
    "max_count_per_answer": 30,
    "max_size_bytes": 20971520   // 20MB
  },
  "forbidden": {
    "clickbait_words": ["震惊"]
  }
}
```

**关键提醒**：不要把 constraints.json 写成"自然语言描述"——它是机器读的，写成 dict / list，每个字段都在 `check_constraints.py` 里被查。

### Step 4：实现 `tools/adapt_html.py`

参考 `platform-wechat/tools/adapt_html.py` 的骨架。**最简实现**只需要这几步：

```python
from bs4 import BeautifulSoup

def adapt_for_zhihu(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    # 1. 剥 <script> / 外部 <link>
    for tag in soup.find_all("script"):
        tag.decompose()
    for link in soup.find_all("link", attrs={"rel": "stylesheet"}):
        link.decompose()
    # 2. 替换 <img data-zhihu-src> 占位
    for img in soup.find_all("img"):
        src = img.get("data-zhihu-src")
        if src:
            img["src"] = src
    # 3. 知乎特定：把 <h1> 转 <h2>（知乎编辑器里 h1 是文章标题，正文不应该用 h1）
    for h1 in soup.find_all("h1"):
        h1.name = "h2"
    return str(soup)
```

CLI 入口照抄 platform-wechat 的 argparse + main() 即可。

### Step 5：实现 `tools/check_constraints.py`

**80% 是复制 platform-wechat 的代码**——改 3 处即可：
1. `DEFAULT_CONSTRAINTS = Path(__file__).parent.parent / "constraints.json"` 路径不用改
2. `check_draft` 函数里改约束引用（"title" / "word_count" / "images" 这些 key 对应 constraints.json 的字段）
3. 加知乎特定的检测（如果有）——比如"答案是否带 '著作权声明'"、"是否使用 markdown 引用块"等

### Step 6：更新 `tools/list-targets`

打开 `tools/list-targets`，在 `TARGETS` 列表里加一项：

```python
{
    "id": "zhihu",
    "name": "知乎",
    "skill_dir": "skills/platform-zhihu",
    "constraints": "skills/platform-zhihu/constraints.json",
    "status": "active",
    "tools_implemented": [
        "skills/platform-zhihu/tools/adapt_html.py",
        "skills/platform-zhihu/tools/check_constraints.py",
    ],
    "tools_planned": [],
    "note": "zhihu skill completed; add to list-targets",
},
```

跑一下确认：

```bash
./tools/list-targets
```

应该看到新平台行。

### Step 7：跑 e2e

```bash
# 1. 建一个新 example 目录
mkdir -p examples/zhihu-test/scratch
cp -r examples/hello-world/scratch/* examples/zhihu-test/scratch/

# 2. 改 spec：把 platforms 改成新平台
./tools/draft-spec \
    --topic "测试知乎" \
    --platforms zhihu \
    --word-count 1500 \
    --out examples/zhihu-test/spec.json

# 3. 渲染 inline HTML
python3 skills/render-html/tools/render.py examples/hello-world/scratch/test.md \
    --title "测试知乎" \
    --output examples/zhihu-test/scratch/article.html

# 4. 平台适配
python3 skills/platform-zhihu/tools/adapt_html.py \
    examples/zhihu-test/scratch/article.html \
    -o examples/zhihu-test/scratch/article-zhihu.html

# 5. 构造 draft 跑约束自检
# （手动构造 draft.json 测，或等 run-pipeline 支持新平台）
python3 skills/platform-zhihu/tools/check_constraints.py examples/zhihu-test/scratch/draft.json
```

### Step 8：commit

```bash
git add skills/platform-zhihu/ tools/list-targets
git commit -m "feat(platform): add zhihu skill

- constraints: 适配知乎字数/排版规则
- adapt_html: 剥 script/外链、h1→h2、占位替换
- check_constraints: 9 条硬约束自检（字数、标题、配图等）
- list-targets: 标记 zhihu 为 active"
```

## 检查清单

完成一个平台 skill 后，过一遍：

- [ ] `SKILL.md` 的 frontmatter `name` 跟目录名一致
- [ ] `SKILL.md` body 里的"工具"列表跟 `tools/` 实际文件一致
- [ ] `constraints.json` 是合法 JSON（`python3 -c "import json; json.load(open(...))"`）
- [ ] `tools/adapt_html.py` 在示例 HTML 上跑过，输出不报错
- [ ] `tools/check_constraints.py` 对"故意不合规"draft 报告 block issues
- [ ] `tools/check_constraints.py` 对"合规"draft 报告 `pass: true`
- [ ] `tools/list-targets` 列出新平台
- [ ] 至少一个 e2e 例子（`examples/<platform>-test/`）跑通

## 常见踩坑

### 1. `AttributeValueList` 类型问题

`BeautifulSoup` 的 `element.get("href", "")` 返回的不是 `str` 而是 `AttributeValueList`（list-like）。pyright 会报"Cannot access attribute startswith"。

修法：
```python
href = a.get("href", "") or ""
if not isinstance(href, str):
    href = " ".join(href) if href else ""
```

### 2. CSS inline 不彻底

`render-html/tools/render.py` 已经做了 inline。但有些 platform 还要做**二次清洗**——比如 `inline_html` 里残留 `<style>` 块（虽然 render 已经移除，防御性再剥一次）。

### 3. 约束的"建议值"和"硬值"混在一起

`constraints.json` 是机器读的，**不要**写自然语言。如果要写"建议每 600-1000 字一张图"——这是结构约束，字段名要规范（比如 `image_every_chars: [600, 1000]`）。

### 4. check_constraints 的 exit code

`return 0` = pass；`return 1` = has block。`has warn/info` **不**算 fail。

### 5. tools/list-targets 的 status 字段

新平台加完就标 `active`；如果加了一半就标 `stub`；如果还没动手就标 `planned`。

## 关联

- 现有平台示例：`skills/platform-wechat/`、`skills/platform-xiaohongshu/`
- 通用工具契约：`skills/render-html/SKILL.md`、`skills/render-image/SKILL.md`
- e2e 流程参考：`examples/hello-world/README.md`
- 架构决策：`docs/ADR-001-agent-native-architecture.md`
