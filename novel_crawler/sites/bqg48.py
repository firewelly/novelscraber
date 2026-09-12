# -*- coding: utf-8 -*-
"""笔趣阁模板家族适配器（Playwright 渲染章节正文，多镜像互备）。

2026-09-12 实测：书页/目录静态可抓（首页探测 25 个活站），章节正文由混淆 JS
渲染，需浏览器。目录链接通用规则：书籍路径下含 .html 且标题含章节特征。
镜像间目录/章节路径同构，同一章节可在兄弟镜像重试（内容可用性随镜像而异）。
"""
import logging
import random
import re
import time

from .base import SiteAdapter, numeric_sort_key, safe_soup
from ..core.meta import BookMeta

log = logging.getLogger("novel_crawler.bqg")

_CHAPTER_TITLE_RE = re.compile(r"第.{1,12}[章回节卷]|序章|楔子|尾声|后记|番外")


class Bqg48Family(SiteAdapter):
    """多镜像笔趣阁家族。mirrors 全部同构（目录/章节相对路径一致）。"""
    needs_render = True

    def fetch_meta(self, book_url):
        html = self.http.get(book_url, referer=self.base())
        soup = safe_soup(html)
        if soup is None:
            return None
        meta = {"title": "", "author": "", "description": ""}
        og = soup.find("meta", property="og:novel:book_name") or \
            soup.find("meta", property="og:title")
        if og:
            meta["title"] = og.get("content", "").strip()
        au = soup.find(string=re.compile(r"作者[：:]"))
        if au:
            m = re.search(r"作者[：:]\s*([^\s<]{1,30})", au if isinstance(au, str) else str(au))
            if m:
                meta["author"] = m.group(1)
        d = soup.find("meta", attrs={"name": "description"})
        if d:
            meta["description"] = d.get("content", "").strip()
        # 作者兜底：简介中的「作家XXX」或标题第3段（章_书名_作者_笔趣阁）
        if not meta["author"] and meta["description"]:
            m2 = re.search(r"作家([^\s，。,：:]{1,20})(?:的最新|所创作)", meta["description"])
            if m2:
                meta["author"] = m2.group(1)
        if not meta["author"]:
            tt = soup.find("title")
            if tt and tt.get_text().count("_") >= 2:
                parts = tt.get_text().split("_")
                if len(parts) >= 3:
                    meta["author"] = parts[2].strip()
        if not meta["title"]:
            t = soup.find("h1")
            meta["title"] = t.get_text(strip=True) if t else ""
            if not meta["title"]:
                tt = soup.find("title")
                meta["title"] = tt.get_text().split("_")[0].strip() if tt else ""
        if not meta["title"]:
            return None
        return BookMeta(title=meta["title"], author=meta["author"],
                        description=meta["description"],
                        source_site=self.site_key, source_url=book_url)

    def fetch_chapters(self, book_url):
        html = self.http.get(book_url, referer=self.base())
        soup = safe_soup(html)
        if soup is None:
            return []
        path_prefix = re.sub(r"^https?://[^/]+", "", book_url)
        if not path_prefix.endswith("/"):
            path_prefix = path_prefix.rsplit("/", 1)[0] + "/"
        chapters, seen = [], set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            # 相对链接同书籍路径；绝对链接须指向本站同路径
            if href.startswith("http"):
                if not href.startswith(self.base()):
                    continue
                if path_prefix not in href:
                    continue
            elif not href.startswith(path_prefix):
                # 模板变体：链接可能在不同前缀（如 /books/N/），但都含 N/N.html
                if not re.search(r"/\d+/\d+\.html$|/\d+_\d+\.html$", href):
                    continue
            text = (a.get("title") or a.get_text(strip=True) or "").strip()
            if not text or not _CHAPTER_TITLE_RE.search(text):
                continue
            full = self.abs_url(href)
            if full in seen:
                continue
            seen.add(full)
            chapters.append((full, text))
        chapters.sort(key=lambda c: numeric_sort_key(c[0]))
        return chapters

    def fetch_content(self, chapter_url, title=""):
        """Playwright 渲染；失败时按顺序尝试兄弟镜像同路径。"""
        candidates = [chapter_url]
        path = re.sub(r"^https?://[^/]+", "", chapter_url)
        for mirror in self.mirrors[1:]:
            candidates.append(mirror.rstrip("/") + path)
        for i, url in enumerate(candidates):
            text = self.renderer.extract_content(url)
            if text:
                return text
            if i < len(candidates) - 1:
                time.sleep(random.uniform(1, 2))
        return None
