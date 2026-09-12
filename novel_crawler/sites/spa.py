# -*- coding: utf-8 -*-
"""SPA 站点家族适配器（xbqk.cc / bqg504.cc / bqg930.cc / bqg329.cc）。

自 work_folder/novel_scraper_with_resume_v2_2.py 移植（H/ 库来源站）：
整站 JS 动态加载，书籍页与章节页都需要 Playwright 渲染。
注意：站点带防爬广告码（bokan9◇cc 等），渲染提取后统一走 clean_watermark。
"""
import re
from urllib.parse import urljoin

from .base import SiteAdapter
from ..core.meta import BookMeta

_CHAPTER_RE = re.compile(r"第|章")


class SpaSite(SiteAdapter):
    site_key = "xbqk"
    mirrors = ("https://www.xbqk.cc",)
    needs_render = True

    def fetch_meta(self, book_url):
        page = self.renderer.goto(book_url, wait_ms=3000)
        title = "未知书名"
        h1 = page.query_selector("h1")
        if h1:
            title = h1.inner_text().strip()
        author = ""
        au = page.query_selector(".author, p.author, span.author")
        if au:
            m = re.search(r"作者[：:]?\s*([^\s]{1,30})", au.inner_text())
            author = m.group(1) if m else au.inner_text().strip()
        desc = ""
        de = page.query_selector(".intro, #intro, .description")
        if de:
            desc = de.inner_text().strip()
        if not title or title == "未知书名":
            return None
        return BookMeta(title=title, author=author, description=desc,
                        source_site=self.site_key, source_url=book_url)

    def fetch_chapters(self, book_url):
        page = self.renderer.goto(book_url, wait_ms=3000)
        chapters, seen = [], set()
        for link in page.query_selector_all("a"):
            try:
                href = link.get_attribute("href")
                text = link.inner_text().strip()
            except Exception:
                continue
            if not href or not text or not _CHAPTER_RE.search(text):
                continue
            if len(text) > 60:      # 排除长推荐文案
                continue
            full = href if href.startswith("http") else urljoin(book_url, href)
            if full in seen:
                continue
            seen.add(full)
            chapters.append((full, text))
        return chapters

    def fetch_content(self, chapter_url, title=""):
        return self.renderer.extract_content(chapter_url, wait_ms=3000)
