"""
test_slice_grid.py —— 锁住 slice_grid.py 的 9 宫格切图行为

P1 锁点: 小红书 9 宫格必须 3x3 切出 9 张 360x480 tile + 1 contact sheet.
P0-B 锁点 (副): 输入尺寸不被整除时 snap-to-grid 行为.

运行：
    cd ~/self-media-pipeline
    python3 tests/test_slice_grid.py
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SLICE_GRID = PLUGIN_ROOT / "skills" / "platform-xiaohongshu" / "tools" / "slice_grid.py"


def make_png(path: Path, width: int, height: int, color="#ff6699"):
    """Create a solid-color PNG at given size."""
    from PIL import Image
    im = Image.new("RGB", (width, height), color)
    im.save(path)
    im.close()


def run_slice(input_png, output_dir, rows=3, cols=3, extra_args=None):
    cmd = [
        sys.executable, str(SLICE_GRID),
        "--input", str(input_png),
        "--output-dir", str(output_dir),
        "--rows", str(rows),
        "--cols", str(cols),
    ]
    if extra_args:
        cmd += extra_args
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return r.returncode, r.stdout, r.stderr


class TestSliceGridBasic(unittest.TestCase):
    """3x3 切图基础契约."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_3x3_grid_produces_9_tiles(self):
        """1080x1440 → 9 张 360x480 tile."""
        inp = self.tmp_dir / "big.png"
        out = self.tmp_dir / "grid"
        make_png(inp, 1080, 1440)

        rc, _, stderr = run_slice(inp, out)
        self.assertEqual(rc, 0, f"slice failed: {stderr}")

        tiles = sorted(out.glob("*.png"))
        tile_names = [p.name for p in tiles]
        # 9 tile + 1 contact-sheet
        for i in range(1, 10):
            self.assertIn(f"{i:02d}.png", tile_names, f"missing tile {i:02d}.png")
        self.assertIn("contact-sheet.png", tile_names)

        # verify each tile is 360x480
        from PIL import Image
        for i in range(1, 10):
            tile_path = out / f"{i:02d}.png"
            im = Image.open(tile_path)
            self.assertEqual(im.size, (360, 480), f"tile {i:02d} size {im.size} != (360, 480)")
            im.close()

    def test_contact_sheet_dimensions(self):
        """contact sheet 尺寸 = input size."""
        inp = self.tmp_dir / "big.png"
        out = self.tmp_dir / "grid"
        make_png(inp, 1080, 1440)
        run_slice(inp, out)

        cs = out / "contact-sheet.png"
        self.assertTrue(cs.exists(), "contact-sheet not created")
        from PIL import Image
        im = Image.open(cs)
        self.assertEqual(im.size, (1080, 1440))
        im.close()

    def test_2x2_grid_produces_4_tiles(self):
        """非 3x3 也应正确切 (2x2 切 4 张)."""
        inp = self.tmp_dir / "big.png"
        out = self.tmp_dir / "grid"
        make_png(inp, 800, 1000)
        run_slice(inp, out, rows=2, cols=2)
        tiles = sorted(p.name for p in out.glob("*.png"))
        for i in range(1, 5):
            self.assertIn(f"{i:02d}.png", tiles)


class TestSliceGridEdgeCases(unittest.TestCase):
    """边界情况."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_non_divisible_size_snap_to_grid(self):
        """1100x1500 (不被 3 整除) → 应当 snap (floor) 到 3x3 grid."""
        inp = self.tmp_dir / "big.png"
        out = self.tmp_dir / "grid"
        make_png(inp, 1100, 1500)

        rc, _, stderr = run_slice(inp, out)
        self.assertEqual(rc, 0, f"snap-to-grid failed: {stderr}")

        # 期望 floor: 1100 → 1098 (3*366), 1500 不变 (3*500)
        # tiles 应为 366 x 500
        from PIL import Image
        for i in range(1, 10):
            im = Image.open(out / f"{i:02d}.png")
            self.assertEqual(im.size, (366, 500), f"tile {i:02d} size {im.size} != (366, 500)")
            im.close()

    def test_nonexistent_input_fails(self):
        """不存在的 input → exit != 0, 错误信息清楚."""
        out = self.tmp_dir / "grid"
        rc, _, stderr = run_slice("/nonexistent/path.png", out)
        self.assertNotEqual(rc, 0, "missing input must fail")
        self.assertTrue(len(stderr) > 0 or "error" in (stderr + "").lower())

    def test_non_png_input_fails(self):
        """非 PNG 文件 (text) → exit != 0."""
        inp = self.tmp_dir / "fake.png"
        inp.write_text("not an image")
        out = self.tmp_dir / "grid"
        rc, _, stderr = run_slice(inp, out)
        self.assertNotEqual(rc, 0, "non-PNG input must fail")

    def test_no_contact_sheet_flag(self):
        """--no-contact-sheet 不生成 contact sheet."""
        inp = self.tmp_dir / "big.png"
        out = self.tmp_dir / "grid"
        make_png(inp, 1080, 1440)
        run_slice(inp, out, extra_args=["--no-contact-sheet"])

        tiles = sorted(p.name for p in out.glob("*.png"))
        self.assertNotIn("contact-sheet.png", tiles)
        # 9 tile 应在
        for i in range(1, 10):
            self.assertIn(f"{i:02d}.png", tiles)


if __name__ == "__main__":
    unittest.main(verbosity=2)
