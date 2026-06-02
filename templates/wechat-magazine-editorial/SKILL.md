---
name: wechat-magazine-editorial
platform: wechat
description: 公众号杂志长文模板。适合深度文章、方法论、案例复盘；用 masthead、超大标题、双栏/单栏正文、pull quote 和编号章节制造出版感。
status: active
default: true
content_type: longform
output_kind: article_html
---

# wechat-magazine-editorial

## 意图

生成一篇可粘贴到微信公众号编辑器的杂志感长文 HTML。适合 1200 字以上内容，强调阅读节奏和视觉记忆点。

## 必须模仿 example.html 的地方

- 顶部 masthead：栏目名、日期、issue 编号。
- 超大 serif headline：标题可分行，允许一个强调词用 accent 色。
- 正文阅读宽度控制在 65ch 左右，段落之间有明显呼吸感。
- 至少使用一种 editorial 组件：pull quote、编号 section、数据条、figure caption。
- 色彩克制：纸感底色、深色正文、一个强调色。

## 禁止

- 不要输出普通 markdown 转 HTML 的单调段落流。
- 不要使用外链图片作为核心视觉。
- 不要依赖 class 样式在公众号里存活；重要样式要能被 `platform-wechat/tools/adapt_html.py` 保留。
