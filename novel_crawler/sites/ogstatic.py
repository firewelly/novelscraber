# -*- coding: utf-8 -*-
"""静态 og:novel 通用适配器：一个类吃掉所有「og:novel 元数据 + 静态章节」站点。

已验证覆盖（2026-09-12）：
- kuaizhui.net   书籍 /tmst/          章节 /tmst/{id}.html           正文 div.content
- xbiquge345.com 书籍 /book/{id}/     章节 /chapter/{id}/{cid}.html  正文 #content（1.8万字/章）
- yebiquge.com   首页/正文静态（zzxx 疑似同构）

章节链接发现策略是通用的：书籍页（或目录页）内所有 .html 链接中，
取「与书籍路径同前缀 + 标题含章节特征」者，按 URL 数字排序。
"""
import re

from .base import SiteAdapter, numeric_sort_key, parse_og_novel, safe_soup
from ..core.meta import BookMeta
from ..core.txtio import clean_text
from ..core.clean import polish

_CHAPTER_TITLE_RE = re.compile(r"第.{1,12}[章回节卷]|序章|楔子|尾声|后记|番外")


class OgStaticSite(SiteAdapter):
    """静态 og:novel 站点通用适配器。

    子类/实例需提供：
      site_key, mirrors
      content_selector: bs4 查找正文的 (attrs dict) 或 selector 列表，逐个尝试
      chapter_scope: 章节链接前缀（相对路径前缀，如 '/tmst/' 或 '/chapter/35247/'）；
                     为空时自动取书籍 URL path + 数字.html 的同前缀
    """
    content_selector = None
    chapter_scope = None
    sort_numeric = False    # 目录默认保持页面顺序（部分站章节 ID 非顺序，数字排序会乱）；zzxx 等旧站显式开启

    # ---- meta ----
    def fetch_meta(self, book_url):
        html = self.http.get(book_url)
        soup = safe_soup(html)
        if soup is None:
            return None
        og = parse_og_novel(soup)
        if not og["title"]:
            # 兜底 <title>
            t = soup.find("title")
            og["title"] = t.get_text().split("_")[0].strip() if t else ""
        if not og["title"]:
            return None
        if not og["description"]:
            d = soup.find("meta", attrs={"name": "description"})
            og["description"] = d.get("content", "").strip() if d else ""
        return BookMeta(
            title=og["title"], author=og["author"], category=og["category"],
            status=og["status"], update_time=og["update_time"],
            description=og["description"],
            source_site=self.site_key, source_url=book_url,
        )

    # ---- 章节列表 ----
    def fetch_chapters(self, book_url):
        html = self.http.get(book_url)
        soup = safe_soup(html)
        if soup is None:
            return []
        # 前缀候选：显式配置 > og:latest_chapter_url 所在目录 > 书籍路径本身
        scopes = []
        if self.chapter_scope:
            scopes.append(self.chapter_scope)
        og_latest = soup.find("meta", property="og:novel:latest_chapter_url")
        if og_latest and og_latest.get("content"):
            path = re.sub(r"^https?://[^/]+", "", og_latest["content"])
            scopes.append(path.rsplit("/", 1)[0] + "/")
        path = re.sub(r"^https?://[^/]+", "", book_url)
        path = re.sub(r"[^/]*\.html$", "", path)
        scopes.append(path if path.endswith("/") else path.rsplit("/", 1)[0] + "/")

        for scope in scopes:
            chapters = self._collect_chapters(soup, scope, book_url)
            if len(chapters) >= 3:
                return chapters
            log.debug("scope=%s 仅命中 %d 章，尝试下一候选", scope, len(chapters))
        # 全部候选失败：返回最多的一组
        best = max((self._collect_chapters(soup, s, book_url) for s in scopes), key=len)
        return best

    def _collect_chapters(self, soup, scope, book_url):
        # 收集所有匹配锚点（记录文档顺序索引）
        hits = []   # (doc_index, url, title)
        seen = set()
        for idx, a in enumerate(soup.find_all("a", href=True)):
            href = a["href"]
            text = (a.get("title") or a.get_text(strip=True) or "").strip()
            full = self.abs_url(href)
            if scope not in full or full in seen:
                continue
            if not re.search(r"\d+\.html$", full.split("#")[0]):
                continue
            if not _CHAPTER_TITLE_RE.search(text):
                continue
            seen.add(full)
            hits.append((idx, full.split("#")[0], text))
        if not hits:
            return []
        # 最大连续块：顶部散落的「最新章节」推荐链接与主目录块分离，只保留主块
        runs, run = [], [hits[0]]
        for h in hits[1:]:
            if h[0] - run[-1][0] <= 8:
                run.append(h)
            else:
                runs.append(run)
                run = [h]
        runs.append(run)
        best = max(runs, key=len)
        chapters = [(u, t) for _, u, t in best]
        if self.sort_numeric:
            chapters.sort(key=lambda c: numeric_sort_key(c[0]))
        return chapters

    # ---- 正文 ----
    def fetch_content(self, chapter_url, title=""):
        html = self.http.get(chapter_url, referer=self.base())
        soup = safe_soup(html)
        if soup is None:
            return None
        div = None
        for selector in (self.content_selector or []):
            try:
                div = soup.select_one(selector)
            except Exception:
                div = None
            if div:
                break
        if div is None:
            # 兜底：最大中文 div
            best, best_n = None, 0
            for d in soup.find_all(["div", "dd", "td"]):
                n = len(re.findall(r"[\u4e00-\u9fff]", d.get_text()))
                if n > best_n:
                    best, best_n = d, n
            div = best if best_n > 300 else None
        if div is None:
            return None
        parts = []
        for node in div.descendants:
            if isinstance(node, str):
                parts.append(node)
            elif node.name in ("br", "p", "div", "tr", "section"):
                parts.append("\n")
        text = clean_text("".join(parts))
        text = re.sub(r"<[^>]+>", "", text)
        # 不做占位提前拒绝：占位行（章节报错/上一章等）由 polish 行清理剔除，
        # 真占位页清理后为空 → 返回 None
        return polish(text)
