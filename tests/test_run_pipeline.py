from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
RUN_PIPELINE = PLUGIN_ROOT / "tools" / "run-pipeline"
REAL_SPEC = PLUGIN_ROOT / "examples" / "01-ai-agent-intro" / "spec.json"
DB_PATH = PLUGIN_ROOT / "library" / "data" / "smp.db"


class TestRunPipelineTemplateSelection(unittest.TestCase):
    def test_real_llm_pipeline_records_template_metadata(self):
        result = subprocess.run(
            [
                sys.executable,
                str(RUN_PIPELINE),
                "--spec",
                str(REAL_SPEC),
                "--real-llm",
                "--skip-render",
            ],
            cwd=PLUGIN_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("templates={'wechat': 'wechat-magazine-editorial'", result.stdout)
        self.assertIn("'xiaohongshu': 'xhs-pastel-card-deck'}", result.stdout)

        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT platform, metadata_json FROM drafts ORDER BY id DESC LIMIT 2"
            ).fetchall()
        metadata_by_platform = {
            row["platform"]: json.loads(row["metadata_json"])
            for row in rows
        }
        self.assertEqual(
            metadata_by_platform["wechat"]["template_id"],
            "wechat-magazine-editorial",
        )
        self.assertEqual(
            metadata_by_platform["xiaohongshu"]["template_id"],
            "xhs-pastel-card-deck",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
