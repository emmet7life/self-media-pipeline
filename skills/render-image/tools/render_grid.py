#!/usr/bin/env python3
"""
render_grid.py —— 把 N 张 HTML（9 宫格源）渲染成 N 张独立 PNG

输入: 一个目录，里面按 01.html / 02.html / ... / NN.html 排序的 HTML 文件
输出: 同名 01.png / 02.png / ... / NN.png + contact-sheet.png

设计原则:
- 9 张图独立可读（不是渲染 1 张大图再切，那样中间 4 张会"看起来像 1 张"）
- 各自用相同 viewport（默认 1080x1440，即小红书单张发布图尺寸）
- contact sheet 用 Pillow 拼成 3x3 预览图，**只供 agent 自检**，不发布

用法:
    python render_grid.py --input-dir renders/xhs/card-html/ --output-dir renders/xhs/card-png/ --rows 3 --cols 3
"""
import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright
from PIL import Image


def render_grid(input_dir: Path, output_dir: Path, rows: int, cols: int, cell_width: int, cell_height: int) -> list[Path]:
    """渲染 N 张 HTML 到 N 张 PNG，返回 PNG 路径列表"""
    if not input_dir.is_dir():
        raise FileNotFoundError(f"input dir not found: {input_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    # 按文件名排序
    html_files = sorted(input_dir.glob("*.html"))
    if not html_files:
        raise ValueError(f"no *.html files in {input_dir}")

    expected_count = rows * cols
    if len(html_files) != expected_count:
        print(f"WARNING: found {len(html_files)} HTML files, expected {expected_count} ({rows}x{cols})", file=sys.stderr)

    png_paths: list[Path] = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": cell_width, "height": cell_height},
            device_scale_factor=1.0,
        )
        for html_file in html_files:
            page = context.new_page()
            page.goto(html_file.resolve().as_uri(), wait_until="networkidle")
            png_path = output_dir / (html_file.stem + ".png")
            page.screenshot(path=str(png_path), full_page=True)
            png_paths.append(png_path)
            page.close()
            print(f"  rendered {html_file.name} -> {png_path.name} ({png_path.stat().st_size} bytes)", file=sys.stderr)
        browser.close()

    return png_paths


def make_contact_sheet(png_paths: list[Path], output: Path, rows: int, cols: int) -> None:
    """用 Pillow 把 N 张 PNG 拼成 rows x cols 大图（带接缝引导线），仅供自检"""
    if not png_paths:
        return
    # 找第一张的实际尺寸
    first = Image.open(png_paths[0])
    cell_w, cell_h = first.size
    first.close()

    sheet_w = cell_w * cols
    sheet_h = cell_h * rows
    sheet = Image.new("RGB", (sheet_w, sheet_h), "white")

    for i, png_path in enumerate(png_paths[: rows * cols]):
        row = i // cols
        col = i % cols
        img = Image.open(png_path)
        # 如果尺寸不一致，resize 到单元格大小
        if img.size != (cell_w, cell_h):
            img = img.resize((cell_w, cell_h), Image.Resampling.LANCZOS)
        sheet.paste(img, (col * cell_w, row * cell_h))
        img.close()

    # 画接缝引导线（红色 1px）
    from PIL import ImageDraw
    draw = ImageDraw.Draw(sheet)
    for c in range(1, cols):
        x = c * cell_w
        draw.line([(x, 0), (x, sheet_h)], fill="red", width=2)
    for r in range(1, rows):
        y = r * cell_h
        draw.line([(0, y), (sheet_w, y)], fill="red", width=2)

    sheet.save(output)
    print(f"  contact sheet -> {output} ({sheet_w}x{sheet_h})", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser(description="Render a grid of HTML files to a grid of PNGs")
    ap.add_argument("--input-dir", required=True, help="dir with NN.html files")
    ap.add_argument("--output-dir", required=True, help="dir for NN.png output")
    ap.add_argument("--rows", type=int, default=3)
    ap.add_argument("--cols", type=int, default=3)
    ap.add_argument("--cell-width", type=int, default=1080, help="per-card viewport width")
    ap.add_argument("--cell-height", type=int, default=1440, help="per-card viewport height")
    ap.add_argument("--no-contact-sheet", action="store_true")
    args = ap.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    png_paths = render_grid(input_dir, output_dir, args.rows, args.cols, args.cell_width, args.cell_height)

    if not args.no_contact_sheet and png_paths:
        contact_sheet = output_dir / "contact-sheet.png"
        make_contact_sheet(png_paths, contact_sheet, args.rows, args.cols)


if __name__ == "__main__":
    main()
