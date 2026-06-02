---
name: render-image
description: |
  HTML → PNG 渲染。给"小红书 9 宫格"和"公众号封面/配图"提供视觉资产。
  本 skill 用 headless chrome 截图，**不依赖 html-anything 项目的任何代码**。
triggers:
  - renderer subagent 必加载
  - 任何需要把 HTML 转成图片的 subagent 必加载
allowed-tools:
  - read_file
  - write_file
  - terminal
inputs:
  - name: html_path
    type: string
    description: 输入 HTML 文件路径（来自 render-html 的产物）
  - name: output_path
    type: string
    description: 输出 PNG 路径
  - name: viewport
    type: object
    description: { width, height } 默认 {1080, 1440}（小红书封面）
  - name: full_page
    type: boolean
    default: true
    description: 是否截整页（true = 适合长图）
---

# render-image —— HTML → PNG 渲染

## 这个 skill 干什么

把 HTML（`render-html` 的产物）渲染成**适合自媒体发布的 PNG**。本 skill 强调"产出图片矩阵"——小红书发布形态是 9 张图，不是 1 张长图。

## 这个 skill 不干什么

- 不写 HTML 排版——那是 `render-html`
- 不切 9 宫格——那是 `platform-xiaohongshu/tools/slice_grid.py`
- 不生成 AI 配图——以后可接 SD / ComfyUI

## 工作流

### 单一图片渲染

```bash
python skills/render-image/tools/render.py \
    --html renders/xhs/cover.html \
    --png  renders/xhs/cover.png \
    --viewport 1080x1440
```

### 9 宫格渲染（小红书专属）

小红书的 9 宫格**应该**是 9 张独立可读的图。**不要**渲染 1 张大图再切——那会让"中间 4 张"看起来是 1 张图。

正确做法：
1. 把内容**先**按 3×3 拆分（每张 360×480）
2. **每张**单独渲染成 PNG
3. 用 `slice_grid.py` 拼成预览 contact sheet（不发布，只自检）

工具：`tools/render_grid.py`（**第 3 周实现**）

```bash
python skills/render-image/tools/render_grid.py \
    --html-grid-dir renders/xhs/grid-html/ \
    --png-grid-dir renders/xhs/grid-png/ \
    --rows 3 --cols 3
```

## 工具实现细节

### `tools/render.py`（核心）

依赖：
- `playwright`（headless chrome）
- Python 3.10+

骨架：

```python
# skills/render-image/tools/render.py
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def render(html_path: str, png_path: str, viewport: dict, full_page: bool = True):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport=viewport)
        await page.goto(Path(html_path).resolve().as_uri())
        await page.screenshot(path=png_path, full_page=full_page)
        await browser.close()

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", required=True)
    ap.add_argument("--png", required=True)
    ap.add_argument("--viewport", default="1080x1440")
    ap.add_argument("--full-page", action="store_true", default=True)
    args = ap.parse_args()
    w, h = map(int, args.viewport.split("x"))
    asyncio.run(render(args.html, args.png, {"width": w, "height": h}, args.full_page))
```

### `tools/render_grid.py`（9 宫格）

详见 `platform-xiaohongshu/SKILL.md` 的工具契约。

## 字体与中文支持

- 系统需安装中文字体（`wqy-microhei` / `noto-cjk` / 等）
- 没有中文字体会出现"豆腐块"
- `tools/check_fonts.py` 自检（**第 3 周实现**）

## 关联

- 上游：`render-html`（喂 HTML 进来）
- 下游：`platform-xiaohongshu/tools/slice_grid.py`（9 宫格切图）
- 不依赖：`html-anything` 任何代码
