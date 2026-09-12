# -*- coding: utf-8 -*-
"""zzxx.org 适配器（自 scrapers/zzxx_crawler.py 泛化移植，含增量扫描与 metadata 补齐）。

网站结构（2026-08/09 实测）：
- 书籍 URL: https://www.zzxx.org/files/article/{vol}/{id}/  （卷号无关，id 唯一）
- 存在性: <meta property="og:novel:book_name">
- 章节列表: <div id="list"> 下 <a href=".../{cid}.html" title="章节名">
- 章节正文: <div id="htmlContent">
"""
import logging
import os
import re
import sqlite3

from .ogstatic import OgStaticSite
from .base import safe_soup
from ..core.meta import BookMeta, now_str, parse_header, header_needs_fix, rebuild

log = logging.getLogger("novel_crawler.zzxx")

SITE_ROOT = "https://www.zzxx.org"
BOOK_URL = SITE_ROOT + "/files/article/72/{bid}/"


class ZzxxSite(OgStaticSite):
    site_key = "zzxx"
    mirrors = (SITE_ROOT,)
    content_selector = ["#htmlContent", "#content"]

    # ---- ogstatic 钩子 ----
    def fetch_chapters(self, book_url):
        """zzxx 章节列表在 div#list 内（避免误抓推荐位链接）"""
        html = self.http.get(book_url)
        soup = safe_soup(html)
        if soup is None:
            return []
        box = soup.find("div", id="list")
        chapters, seen = [], set()
        for a in (box.find_all("a", href=re.compile(r"\.html$")) if box else []):
            href = a.get("href", "")
            title = (a.get("title") or a.get_text(strip=True) or "").strip()
            if href and title:
                full = self.abs_url(href, book_url)
                if full not in seen:
                    seen.add(full)
                    chapters.append((full, title))
        chapters.sort(key=lambda c: int(re.search(r"(\d+)\.html", c[0]).group(1))
                      if re.search(r"(\d+)\.html", c[0]) else 0)
        return chapters

    def book_url(self, bid):
        return BOOK_URL.format(bid=bid)

    # ---- 增量扫描状态（优先沿用既有 scrapers/zzxx_crawler.db；独立发行版用 cwd）----
    class _State:
        @staticmethod
        def _resolve_db():
            env = os.environ.get("ZZXX_DB")
            if env:
                return env
            candidates = [
                # 项目内：src/novel_crawler/sites → 项目根/scrapers/zzxx_crawler.db
                os.path.normpath(os.path.join(
                    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                    "scrapers", "zzxx_crawler.db")),
                # 独立发行版：当前工作目录
                os.path.abspath("zzxx_crawler.db"),
            ]
            for p in candidates:
                if os.path.exists(p):
                    return p
            return candidates[-1]

        def __init__(self, db_path=None):
            self.path = db_path or self._resolve_db()
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            self.conn = sqlite3.connect(self.path)
            self.conn.row_factory = sqlite3.Row
            c = self.conn.cursor()
            c.execute("""CREATE TABLE IF NOT EXISTS crawl_state (
                id INTEGER PRIMARY KEY CHECK (id=1),
                last_scanned_id INTEGER DEFAULT 0,
                last_homepage_max_id INTEGER DEFAULT 0,
                last_run_at TEXT, total_found INTEGER DEFAULT 0,
                total_downloaded INTEGER DEFAULT 0)""")
            c.execute("""CREATE TABLE IF NOT EXISTS novels (
                id INTEGER PRIMARY KEY, title TEXT, author TEXT, category TEXT,
                status TEXT, update_time TEXT, description TEXT,
                chapter_count INTEGER DEFAULT 0, downloaded INTEGER DEFAULT 0,
                file_path TEXT, first_seen TEXT, last_checked TEXT)""")
            c.execute("INSERT OR IGNORE INTO crawl_state (id) VALUES (1)")
            try:
                self.conn.execute("ALTER TABLE novels ADD COLUMN description TEXT")
            except sqlite3.OperationalError:
                pass
            self.conn.commit()

        def state(self):
            return dict(self.conn.execute("SELECT * FROM crawl_state WHERE id=1").fetchone())

        def update(self, **kw):
            sets = ", ".join(f"{k}=?" for k in kw)
            self.conn.execute(f"UPDATE crawl_state SET {sets} WHERE id=1", list(kw.values()))
            self.conn.commit()

        def downloaded_ids(self):
            return {r["id"] for r in self.conn.execute(
                "SELECT id FROM novels WHERE downloaded=1")}

        def downloaded_rows(self):
            return self.conn.execute("SELECT * FROM novels WHERE downloaded=1").fetchall()

    # ---- 首页最新 id ----
    def homepage_max_id(self):
        html = self.http.get(SITE_ROOT + "/")
        soup = safe_soup(html)
        if soup is None:
            return None
        for h2 in soup.find_all("h2"):
            if h2.get_text(strip=True) == "最新添加":
                box = h2.find_parent("div") or h2.parent
                ids = [int(m.group(1)) for a in box.find_all("a", href=True)
                       if (m := re.search(r"/files/article/\d+/(\d+)/", a.get("href", "")))]
                if ids:
                    return max(ids)
        return None

    def probe(self, bid):
        """探测书籍存在性，返回 BookMeta 或 None"""
        url = self.book_url(bid)
        meta = self.fetch_meta(url)
        if meta and meta.title:
            meta.source_site = self.site_key
            meta.source_url = url
            return meta
        return None

    # ---- 旧文件 metadata 补齐 ----
    def fix_file_metadata(self, fp, meta=None):
        """若 TXT 头部缺简介/完整来源 URL，则从站点重新抓取并重写头部。

        meta 可传入已在 DB 中保存的旧字段（title/author 兜底）。
        返回 True 表示已修复。
        """
        if not os.path.exists(fp):
            return False
        with open(fp, encoding="utf-8", errors="ignore") as f:
            text = f.read()
        old = parse_header(text)
        if not header_needs_fix(old):
            return False
        # 从旧头部/DB 恢复 id 以拼 URL
        bid = None
        m = re.search(r"id[=(](\d+)", old.source_site + " " + old.source_url)
        if m:
            bid = int(m.group(1))
        if bid is None and meta:
            bid = meta.get("id") if isinstance(meta, dict) else None
        if not bid:
            log.warning("[fix] %s 无法恢复书籍 id，跳过", fp)
            return False
        fresh = self.probe(bid)
        if not fresh:
            log.warning("[fix] id=%s 站点已不可访问，跳过", bid)
            return False
        # 首章标题用于精确定位章节体起点
        chapters = self.fetch_chapters(self.book_url(bid))
        first_title = chapters[0][1] if chapters else None
        # 保留旧头部里有而新抓取缺失的字段
        fresh.description = fresh.description or old.description
        fresh.author = fresh.author or old.author or "未知"
        new_text = rebuild(text, fresh, first_title)
        with open(fp, "w", encoding="utf-8", errors="ignore") as f:
            f.write(new_text)
        log.info("[fix] %s 头部已升级到 v3（含简介/完整来源URL）", fp)
        return True
