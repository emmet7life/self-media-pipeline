#!/usr/bin/env python3
"""
library/server.py —— L1 内容库的 MCP server 骨架

按 stdio MCP 协议暴露 library.* 工具给 agent 调用。
本文件是**第 1-2 周的最小可工作版本**——只暴露 self-media-pipeline Step 6 真正需要的工具。

完整工具契约见 ../skills/library-mcp/SKILL.md
"""
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

# 定位数据库文件
DB_PATH = Path(__file__).parent / "data" / "smp.db"


def get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ---- MCP protocol helpers (stdio, JSON-RPC 2.0) ----

def send(msg: dict) -> None:
    """Send a JSON-RPC message to stdout (one line, newline-delimited)."""
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def read_msg() -> dict | None:
    """Read one JSON-RPC message from stdin."""
    line = sys.stdin.readline()
    if not line:
        return None
    return json.loads(line)


# ---- Tool implementations ----

def tool_insert_article(args: dict) -> dict:
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO articles (topic, source_material, style_reference, spec_yaml) VALUES (?, ?, ?, ?)",
            (
                args["topic"],
                args.get("source_material"),
                args.get("style_reference"),
                args.get("spec_yaml"),
            ),
        )
        return {"article_id": cur.lastrowid}


def tool_insert_draft(args: dict) -> dict:
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO drafts
               (article_id, platform, status, title, body_markdown, inline_html, metadata_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                args["article_id"],
                args["platform"],
                args.get("status", "draft"),
                args.get("title"),
                args["body_markdown"],
                args.get("inline_html"),
                args.get("metadata_json"),
            ),
        )
        return {"draft_id": cur.lastrowid}


def tool_insert_derivative(args: dict) -> dict:
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO derivatives (draft_id, kind, file_path, mime, size_bytes)
               VALUES (?, ?, ?, ?, ?)""",
            (
                args["draft_id"],
                args["kind"],
                args["file_path"],
                args.get("mime"),
                args.get("size_bytes"),
            ),
        )
        return {"derivative_id": cur.lastrowid}


def tool_list_articles(args: dict) -> dict:
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, topic, created_at FROM articles
               WHERE (? IS NULL OR created_at >= ?)
               ORDER BY created_at DESC
               LIMIT ? OFFSET ?""",
            (
                args.get("since"),
                args.get("since"),
                args.get("limit", 20),
                args.get("offset", 0),
            ),
        ).fetchall()
        return {"articles": [dict(r) for r in rows]}


def tool_search_articles(args: dict) -> dict:
    with get_db() as conn:
        rows = conn.execute(
            """SELECT a.id, a.topic, snippet(articles_fts, 1, '<mark>', '</mark>', '...', 16) AS snippet
               FROM articles_fts
               JOIN articles a ON a.id = articles_fts.rowid
               WHERE articles_fts MATCH ?
               ORDER BY rank
               LIMIT 20""",
            (args["query"],),
        ).fetchall()
        return {"matches": [dict(r) for r in rows]}


def tool_get_article(args: dict) -> dict:
    with get_db() as conn:
        article = conn.execute(
            "SELECT * FROM articles WHERE id = ?", (args["article_id"],)
        ).fetchone()
        if not article:
            return {"error": "not_found"}
        drafts = conn.execute(
            "SELECT * FROM drafts WHERE article_id = ? ORDER BY platform", (args["article_id"],)
        ).fetchall()
        derivatives = []
        for d in drafts:
            dvs = conn.execute(
                "SELECT * FROM derivatives WHERE draft_id = ?", (d["id"],)
            ).fetchall()
            derivatives.extend(dvs)
        return {
            **dict(article),
            "drafts": [dict(d) for d in drafts],
            "derivatives": [dict(dv) for dv in derivatives],
        }


def tool_log_publish(args: dict) -> dict:
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO publish_log (derivative_id, platform_account, publish_url, status, error_message)
               VALUES (?, ?, ?, ?, ?)""",
            (
                args["derivative_id"],
                args["platform_account"],
                args.get("publish_url"),
                args.get("status", "success"),
                args.get("error_message"),
            ),
        )
        return {"publish_log_id": cur.lastrowid}


# ---- MCP dispatch ----

TOOLS = {
    "library.insert_article": tool_insert_article,
    "library.insert_draft": tool_insert_draft,
    "library.insert_derivative": tool_insert_derivative,
    "library.list_articles": tool_list_articles,
    "library.search_articles": tool_search_articles,
    "library.get_article": tool_get_article,
    "library.log_publish": tool_log_publish,
}


def handle_request(req: dict) -> dict:
    method = req.get("method")
    req_id = req.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "self-media-pipeline-library", "version": "0.1.0"},
                "capabilities": {"tools": {}},
            },
        }

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": name,
                        "description": f"self-media-pipeline library tool: {name}",
                        "inputSchema": {"type": "object"},  # 完整 schema 见 skills/library-mcp/SKILL.md
                    }
                    for name in TOOLS
                ]
            },
        }

    if method == "tools/call":
        params = req.get("params", {})
        name = params.get("name")
        args = params.get("arguments", {})
        if name not in TOOLS:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"unknown tool: {name}"}}
        try:
            result = TOOLS[name](args)
            return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": json.dumps(result)}]}}
        except Exception as e:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32000, "message": str(e)}}

    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"method not found: {method}"}}


def main() -> None:
    # stdio MCP loop
    while True:
        try:
            req = read_msg()
        except (EOFError, KeyboardInterrupt):
            break
        if req is None:
            break
        resp = handle_request(req)
        send(resp)


if __name__ == "__main__":
    main()
