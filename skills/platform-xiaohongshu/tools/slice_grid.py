#!/usr/bin/env python3
from __future__ import annotations
"""
slice_grid.py —— 小红书 9 宫格切图工具（核心工具）

把一张大图按 rows x cols 等分成 N 张切片，并额外输出一张带红色接缝引导线的
contact sheet 供 agent 自检（不发布）。

行为契约（与 skills/platform-xiaohongshu/SKILL.md "工具" 小节一致）:

  - 输入: 一张 PNG（典型为 1080 x 1440，由 render-image 生成）
  - 输出: N 张切片 PNG（文件名 01.png ... NN.png，从左到右、从上到下），
          以及一张 contact-sheet.png（把 N 张切片按原顺序拼回 rows x cols 大图，
          带 1-2 px 红色接缝引导线）

边界处理:
  - 输入图片尺寸不被 rows x cols 整除 → 等比 resize 到最近的整数倍后再切
    (不放大/缩小宽高比，只取 floor 维度以避免内容溢出/被裁)
  - 输出目录不存在 → 自动 mkdir(parents=True, exist_ok=True)
  - 输入文件不存在 → 抛 FileNotFoundError，消息明确

用法:
    python3 slice_grid.py \\
        --input renders/xhs/cover.png \\
        --output-dir renders/xhs/grid/ \\
        --rows 3 --cols 3

    python3 slice_grid.py \\
        --input in.png --output-dir out/ --no-contact-sheet

CLI:
    --input            必填，输入 PNG 路径
    --output-dir       必填，输出目录（不存在会自动创建）
    --rows             网格行数，默认 3
    --cols             网格列数，默认 3
    --no-contact-sheet 关闭 contact sheet 输出
    --seam-px          接缝引导线宽度（px），默认 2
    --seam-color       接缝引导线颜色（CSS 颜色或 #RRGGBB），默认 red
    -q, --quiet        静默模式（只把致命错误打到 stderr）

退出码:
    0 成功
    2 参数/IO 错误
    1 未捕获异常
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from PIL import Image, ImageDraw


# --- 常量（与 skills/platform-xiaohongshu/constraints.json 保持一致） ---------
DEFAULT_ROWS: int = 3
DEFAULT_COLS: int = 3
DEFAULT_SEAM_PX: int = 2
DEFAULT_SEAM_COLOR: str = "red"


# --- 异常类型 ---------------------------------------------------------------
class SliceGridError(RuntimeError):
    """slice_grid.py 自身的可控错误（参数/IO）。"""


# --- 纯函数（便于将来加 unit test） ------------------------------------------
def snap_size_to_grid(
    width: int,
    height: int,
    rows: int,
    cols: int,
) -> tuple[int, int]:
    """把 (w, h) 等比向下取整到能被 (cols, rows) 整除的最近整数倍。

    注意：是 *向下* floor，不是 round——这样能保证 resize 后的图被完整切成
    rows x cols 不溢出、不裁掉内容。resize 在调用方完成（用 LANCZOS）。
    """
    if rows <= 0 or cols <= 0:
        raise SliceGridError(f"rows/cols 必须 > 0, got rows={rows} cols={cols}")
    new_w = (width // cols) * cols
    new_h = (height // rows) * rows
    if new_w <= 0 or new_h <= 0:
        raise SliceGridError(
            f"input {width}x{height} 太小，无法切成 {rows}x{cols} "
            f"(需要至少 {cols}x{rows} 像素)"
        )
    return new_w, new_h


def slice_image(
    img: Image.Image,
    rows: int = DEFAULT_ROWS,
    cols: int = DEFAULT_COLS,
) -> list[Image.Image]:
    """把一张图按 rows x cols 等分成 N 张子图（从左到右、从上到下）。

    要求 img 尺寸已被调用方等比 resize 到 (cols*tw, rows*th) 的整数倍。
    """
    if rows <= 0 or cols <= 0:
        raise SliceGridError(f"rows/cols 必须 > 0, got rows={rows} cols={cols}")

    width, height = img.size
    tile_w, tile_h = width // cols, height // rows
    if tile_w <= 0 or tile_h <= 0:
        raise SliceGridError(
            f"size {width}x{height} 切不出 {rows}x{cols} 个非空 tile"
        )

    tiles: list[Image.Image] = []
    for r in range(rows):
        for c in range(cols):
            left = c * tile_w
            upper = r * tile_h
            tiles.append(img.crop((left, upper, left + tile_w, upper + tile_h)))
    return tiles


def build_contact_sheet(
    tiles: Sequence[Image.Image],
    rows: int,
    cols: int,
    seam_px: int = DEFAULT_SEAM_PX,
    seam_color: str = DEFAULT_SEAM_COLOR,
) -> Image.Image:
    """把 N 张切片按原顺序拼回 rows x cols 大图，并画红色接缝引导线。

    seam_px: 引导线宽度（px），0 表示不画引导线
    seam_color: 任何 PIL ImageColor 接受的值（"red" / "#ff0000" / (255,0,0)）
    """
    if not tiles:
        raise SliceGridError("build_contact_sheet: tiles 为空")
    if len(tiles) != rows * cols:
        raise SliceGridError(
            f"build_contact_sheet: tiles 数量 {len(tiles)} != rows*cols={rows*cols}"
        )

    tw, th = tiles[0].size
    sheet = Image.new("RGB", (tw * cols, th * rows), (255, 255, 255))
    for idx, tile in enumerate(tiles):
        r, c = divmod(idx, cols)
        sheet.paste(tile, (c * tw, r * th))

    if seam_px > 0:
        draw = ImageDraw.Draw(sheet)
        # 画列间竖线（不算最右边那条之外）
        for c in range(1, cols):
            x = c * tw
            # 一条 px 宽的线画 seam_px 次，确保视觉上够显眼
            for k in range(seam_px):
                draw.line([(x + k, 0), (x + k, sheet.height)], fill=seam_color)
        # 画行间横线
        for r in range(1, rows):
            y = r * th
            for k in range(seam_px):
                draw.line([(0, y + k), (sheet.width, y + k)], fill=seam_color)

    return sheet


# --- CLI 入口 ---------------------------------------------------------------
def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        prog="slice_grid.py",
        description="Slice a PNG into an NxM grid of tiles (xiaohongshu 9-grid).",
    )
    ap.add_argument("--input", required=True, help="input PNG path")
    ap.add_argument("--output-dir", required=True, help="output directory (auto-created)")
    ap.add_argument("--rows", type=int, default=DEFAULT_ROWS, help=f"rows (default {DEFAULT_ROWS})")
    ap.add_argument("--cols", type=int, default=DEFAULT_COLS, help=f"cols (default {DEFAULT_COLS})")
    ap.add_argument(
        "--no-contact-sheet",
        action="store_true",
        help="skip writing contact-sheet.png",
    )
    ap.add_argument(
        "--seam-px",
        type=int,
        default=DEFAULT_SEAM_PX,
        help=f"seam guide width in px (default {DEFAULT_SEAM_PX})",
    )
    ap.add_argument(
        "--seam-color",
        default=DEFAULT_SEAM_COLOR,
        help=f"seam guide color (default {DEFAULT_SEAM_COLOR})",
    )
    ap.add_argument("-q", "--quiet", action="store_true", help="suppress progress output")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)

    # 1) 输入存在性（明确消息，不靠 PIL 抛一个 confusing 的 "cannot identify"）
    if not input_path.exists():
        print(f"ERROR: input not found: {input_path}", file=sys.stderr)
        return 2
    if not input_path.is_file():
        print(f"ERROR: input is not a regular file: {input_path}", file=sys.stderr)
        return 2

    # 2) 读 PNG（Pillow 12+ Resampling.LANCZOS）
    try:
        img = Image.open(input_path)
        img.load()  # 立刻 decode，避免后面 crop 时才发现 broken file
    except FileNotFoundError:
        # 兜底（理论上已被上面的 exists() 拦住）
        print(f"ERROR: input not found: {input_path}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: cannot read PNG {input_path}: {exc}", file=sys.stderr)
        return 2

    width, height = img.size
    if img.mode != "RGB":
        img = img.convert("RGB")

    # 3) 边界：尺寸不被 rows x cols 整除 → 等比 resize（floor 到最近整数倍）
    if width % args.cols != 0 or height % args.rows != 0:
        new_w, new_h = snap_size_to_grid(width, height, args.rows, args.cols)
        if not args.quiet:
            print(
                f"INFO: input {width}x{height} 不被 {args.rows}x{args.cols} 整除, "
                f"resize 到 {new_w}x{new_h}",
                file=sys.stderr,
            )
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # 4) 切片
    tiles = slice_image(img, rows=args.rows, cols=args.cols)
    n = len(tiles)

    # 5) 输出目录不存在 → mkdir
    output_dir.mkdir(parents=True, exist_ok=True)

    # 6) 写切片 PNG：01.png ... NN.png
    pad = max(2, len(str(n)))
    for idx, tile in enumerate(tiles, start=1):
        out = output_dir / f"{idx:0{pad}d}.png"
        tile.save(out, format="PNG")

    # 7) 可选 contact sheet
    wrote_sheet = False
    if not args.no_contact_sheet:
        sheet = build_contact_sheet(
            tiles,
            rows=args.rows,
            cols=args.cols,
            seam_px=max(0, args.seam_px),
            seam_color=args.seam_color,
        )
        sheet_path = output_dir / "contact-sheet.png"
        sheet.save(sheet_path, format="PNG")
        wrote_sheet = True

    if not args.quiet:
        tile_w, tile_h = tiles[0].size
        print(
            f"wrote {n} tiles ({tile_w}x{tile_h} each) to {output_dir}",
            file=sys.stderr,
        )
        if wrote_sheet:
            print(
                f"wrote contact sheet ({tile_w * args.cols}x{tile_h * args.rows}, "
                f"seam={args.seam_px}px {args.seam_color}) to "
                f"{output_dir / 'contact-sheet.png'}",
                file=sys.stderr,
            )

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SliceGridError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        sys.exit(130)
    except Exception as exc:  # noqa: BLE001
        print(f"FATAL: {exc}", file=sys.stderr)
        sys.exit(1)
