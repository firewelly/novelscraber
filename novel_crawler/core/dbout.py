# -*- coding: utf-8 -*-
"""数据库输出模式（novels + chapters 两表；自旧 zzxx_crawler 的 txt+db 双写设计泛化）。

- novels: 一本书一行，含 v3 全部元数据（title/author/source_site/source_url/...）
- chapters: 每章一行（novel_id, chapter_index, title, content, url），UNIQUE(novel_id, chapter_index)

DB 同时也是续传状态源之一：existing_titles 可查 DB 中已入库章节。
"""
import logging
import os
import sqlite3

from .meta import now_str

log = logging.getLogger("novel_crawler.dbout")

SCHEMA = """
CREATE TABLE IF NOT EXISTS novels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT DEFAULT '',
    category TEXT DEFAULT '',
    status TEXT DEFAULT '',
    update_time TEXT DEFAULT '',
    description TEXT DEFAULT '',
    source_site TEXT DEFAULT '',
    source_url TEXT DEFAULT '',
    chapter_count INTEGER DEFAULT 0,
    crawl_time TEXT DEFAULT '',
    UNIQUE(title, source_site)
);
CREATE TABLE IF NOT EXISTS chapters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    novel_id INTEGER NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    chapter_index INTEGER NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    url TEXT DEFAULT '',
    UNIQUE(novel_id, chapter_index)
);
CREATE INDEX IF NOT EXISTS idx_chapters_novel ON chapters(novel_id);
"""


class NovelDB:
    def __init__(self, path):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass

    def get_novel(self, title, source_site=""):
        row = self.conn.execute(
            "SELECT * FROM novels WHERE title=? AND source_site=?",
            (title, source_site)).fetchone()
        return dict(row) if row else None

    def upsert_novel(self, meta, chapter_count):
        """按 (title, source_site) 定位；返回 novel_id"""
        cur = self.conn.execute(
            "INSERT INTO novels (title,author,category,status,update_time,description,"
            " source_site,source_url,chapter_count,crawl_time)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)"
            " ON CONFLICT(title, source_site) DO UPDATE SET"
            " author=excluded.author, category=excluded.category, status=excluded.status,"
            " update_time=excluded.update_time, description=excluded.description,"
            " source_url=excluded.source_url, chapter_count=excluded.chapter_count,"
            " crawl_time=excluded.crawl_time",
            (meta.title, meta.author, meta.category, meta.status, meta.update_time,
             meta.description, meta.source_site, meta.source_url,
             chapter_count, meta.crawl_time or now_str()))
        self.conn.commit()
        row = self.conn.execute(
            "SELECT id FROM novels WHERE title=? AND source_site=?",
            (meta.title, meta.source_site)).fetchone()
        return row["id"]

    def existing_titles(self, title, source_site, chapter_titles):
        """DB 续传：返回 (novel_id, 已存在标题集合)。novel 不存在时 novel_id 为 None。"""
        row = self.conn.execute(
            "SELECT id FROM novels WHERE title=? AND source_site=?",
            (title, source_site)).fetchone()
        if not row:
            return None, set()
        titles = set()
        for t in chapter_titles:
            hit = self.conn.execute(
                "SELECT 1 FROM chapters WHERE novel_id=? AND title=? LIMIT 1",
                (row["id"], t)).fetchone()
            if hit:
                titles.add(t)
        return row["id"], titles

    def load_contents(self, novel_id):
        """回读该书全部已入库章节 {title: content}（续传合并用）"""
        rows = self.conn.execute(
            "SELECT title, content FROM chapters WHERE novel_id=? ORDER BY chapter_index",
            (novel_id,)).fetchall()
        return {r["title"]: r["content"] for r in rows}

    def replace_chapters(self, novel_id, chapters, contents, urls=None):
        """按目录顺序重写该书全部已获得章节（缺失章跳过，留待续传）"""
        self.conn.execute("DELETE FROM chapters WHERE novel_id=?", (novel_id,))
        n = 0
        for idx, (_, title) in enumerate(chapters, 1):
            content = contents.get(title)
            if not content:
                continue
            url = (urls or {}).get(title, "") if urls else ""
            self.conn.execute(
                "INSERT INTO chapters (novel_id, chapter_index, title, content, url)"
                " VALUES (?,?,?,?,?)", (novel_id, idx, title, content, url))
            n += 1
        self.conn.commit()
        return n

    def stats(self):
        t = self.conn.execute("SELECT COUNT(*) c FROM novels").fetchone()["c"]
        c = self.conn.execute("SELECT COUNT(*) c FROM chapters").fetchone()["c"]
        return t, c
