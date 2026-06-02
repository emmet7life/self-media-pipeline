-- self-media-pipeline library schema
-- 数据库位置: library/data/smp.db
-- 创建命令: sqlite3 library/data/smp.db < library/schema.sql
--
-- 设计原则:
-- 1. articles = 一次内容生产任务的源头（topic + 原料 + 风格参考）
-- 2. drafts = 针对某个平台的草稿（一篇文章可能多平台多版本）
-- 3. derivatives = draft 派生的可发布产物（HTML / PNG / 切图 / 预览）
-- 4. publish_log = 一次发布的审计记录
-- 5. FTS5 = 全文搜索

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- 一篇文章 = 一次"想写点啥"的源头
CREATE TABLE IF NOT EXISTS articles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    topic           TEXT NOT NULL,
    source_material TEXT,
    style_reference TEXT,
    spec_yaml       TEXT,                          -- self-media-pipeline Step 1 产出的 spec
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_articles_created_at ON articles(created_at DESC);

-- 一篇文章的一个平台版本 = 一个 draft
-- status 流转: draft -> reviewed -> needs_human/approved
CREATE TABLE IF NOT EXISTS drafts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id      INTEGER NOT NULL,
    platform        TEXT NOT NULL CHECK (platform IN ('wechat', 'xiaohongshu')),
    status          TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'reviewed', 'needs_human', 'approved')),
    title           TEXT,
    body_markdown   TEXT NOT NULL,
    inline_html     TEXT,
    metadata_json   TEXT,                          -- 平台特定的元数据（字数、reading_time 等）
    review_json     TEXT,                          -- fact-check 报告 JSON
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
);

CREATE INDEX idx_drafts_article ON drafts(article_id);
CREATE INDEX idx_drafts_platform_status ON drafts(platform, status);
CREATE INDEX idx_drafts_created_at ON drafts(created_at DESC);

-- draft 的可发布产物（一对一/多对多）
-- kind 枚举:
--   html_wechat     公众号可粘贴 HTML
--   png_cover       小红书封面图（1080x1440）
--   png_grid        小红书 9 宫格单图（360x480）
--   preview_html    浏览器预览 HTML
--   source_md       原始 markdown 备份
CREATE TABLE IF NOT EXISTS derivatives (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    draft_id        INTEGER NOT NULL,
    kind            TEXT NOT NULL CHECK (kind IN ('html_wechat', 'png_cover', 'png_grid', 'preview_html', 'source_md', 'adapted_html')),
    file_path       TEXT NOT NULL,                 -- 相对 library/ 的路径
    mime            TEXT,
    size_bytes      INTEGER,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (draft_id) REFERENCES drafts(id) ON DELETE CASCADE
);

CREATE INDEX idx_derivatives_draft ON derivatives(draft_id);
CREATE INDEX idx_derivatives_kind ON derivatives(kind);

-- 发布记录
CREATE TABLE IF NOT EXISTS publish_log (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    derivative_id       INTEGER NOT NULL,
    platform_account    TEXT NOT NULL,             -- e.g. "wechat:official_account_x"
    publish_url         TEXT,                      -- 发布后的公开 URL
    published_at        TEXT NOT NULL DEFAULT (datetime('now')),
    status              TEXT NOT NULL DEFAULT 'success' CHECK (status IN ('success', 'failed', 'pending_review')),
    error_message       TEXT,
    FOREIGN KEY (derivative_id) REFERENCES derivatives(id) ON DELETE CASCADE
);

CREATE INDEX idx_publish_log_derivative ON publish_log(derivative_id);
CREATE INDEX idx_publish_log_published_at ON publish_log(published_at DESC);

-- FTS5 全文搜索（articles.topic + drafts.body_markdown）
CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
    topic,
    source_material,
    content='articles',
    content_rowid='id'
);

CREATE VIRTUAL TABLE IF NOT EXISTS drafts_fts USING fts5(
    title,
    body_markdown,
    content='drafts',
    content_rowid='id'
);

-- 触发器: 同步 FTS
CREATE TRIGGER IF NOT EXISTS articles_ai AFTER INSERT ON articles BEGIN
    INSERT INTO articles_fts(rowid, topic, source_material) VALUES (new.id, new.topic, new.source_material);
END;

CREATE TRIGGER IF NOT EXISTS articles_ad AFTER DELETE ON articles BEGIN
    INSERT INTO articles_fts(articles_fts, rowid, topic, source_material) VALUES('delete', old.id, old.topic, old.source_material);
END;

CREATE TRIGGER IF NOT EXISTS articles_au AFTER UPDATE ON articles BEGIN
    INSERT INTO articles_fts(articles_fts, rowid, topic, source_material) VALUES('delete', old.id, old.topic, old.source_material);
    INSERT INTO articles_fts(rowid, topic, source_material) VALUES (new.id, new.topic, new.source_material);
END;

CREATE TRIGGER IF NOT EXISTS drafts_ai AFTER INSERT ON drafts BEGIN
    INSERT INTO drafts_fts(rowid, title, body_markdown) VALUES (new.id, new.title, new.body_markdown);
END;

CREATE TRIGGER IF NOT EXISTS drafts_ad AFTER DELETE ON drafts BEGIN
    INSERT INTO drafts_fts(drafts_fts, rowid, title, body_markdown) VALUES('delete', old.id, old.title, old.body_markdown);
END;

CREATE TRIGGER IF NOT EXISTS drafts_au AFTER UPDATE ON drafts BEGIN
    INSERT INTO drafts_fts(drafts_fts, rowid, title, body_markdown) VALUES('delete', old.id, old.title, old.body_markdown);
    INSERT INTO drafts_fts(rowid, title, body_markdown) VALUES (new.id, new.title, new.body_markdown);
END;
