#!/usr/bin/env python3
"""
render.py —— 把 HTML 渲染成 PNG（用 headless chromium）

输入: HTML 文件路径
输出: PNG 文件路径

默认 viewport: 1080x1440（小红书封面比例 3:4）
full_page=True 默认（适合长图）

用法:
    python render.py --html article.html --png article.png
    python render.py --html article.html --png article.png --viewport 1080x1920 --no-full-page
"""
import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright
from typing import Any, cast


def parse_viewport(s: str) -> dict:
    """Parse 'WIDTHxHEIGHT' to {width, height}"""
    if "x" not in s:
        raise ValueError(f"invalid viewport: {s!r}, expected WIDTHxHEIGHT")
    w, h = s.split("x", 1)
    return {"width": int(w), "height": int(h)}


def render_html_to_png(html_path: Path, png_path: Path, viewport: dict, full_page: bool, device_scale: float) -> None:
    if not html_path.exists():
        raise FileNotFoundError(f"html not found: {html_path}")
    png_path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport=cast("Any", viewport), device_scale_factor=device_scale)
        page = context.new_page()
        # file:// 协议让 headless chrome 直接打开本地 HTML
        page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
        page.screenshot(path=str(png_path), full_page=full_page)
        browser.close()


def main() -> None:
    ap = argparse.ArgumentParser(description="Render HTML to PNG via headless chromium")
    ap.add_argument("--html", required=True, help="input HTML file path")
    ap.add_argument("--png", required=True, help="output PNG file path")
    ap.add_argument("--viewport", default="1080x1440", help="viewport WIDTHxHEIGHT (default 1080x1440)")
    ap.add_argument("--no-full-page", action="store_true", help="capture only viewport, not full page")
    ap.add_argument("--scale", type=float, default=1.0, help="device scale factor (1=72dpi, 2=retina)")
    args = ap.parse_args()

    viewport = parse_viewport(args.viewport)
    html_path = Path(args.html)
    png_path = Path(args.png)

    render_html_to_png(
        html_path=html_path,
        png_path=png_path,
        viewport=viewport,
        full_page=not args.no_full_page,
        device_scale=args.scale,
    )
    size = png_path.stat().st_size
    print(f"wrote {png_path} ({size} bytes, viewport={viewport}, full_page={not args.no_full_page}, scale={args.scale})", file=sys.stderr)


if __name__ == "__main__":
    main()
