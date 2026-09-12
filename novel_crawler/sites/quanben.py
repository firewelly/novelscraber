# -*- coding: utf-8 -*-
"""全本小说网 quanben-xiaoshuo.com（静态，无 og:novel，正文为长 <p> 段落）。

结构（2026-09-12 实测）：
- 书籍页: https://quanben-xiaoshuo.com/n/{slug}/
- 目录页: {书籍页}xiaoshuo.html
- 章节:   /n/{slug}/{id}.html，正文为多个长 <p> 段落
"""
import re

from .base import SiteAdapter, safe_soup
from ..core.meta import BookMeta
from ..core.txtio import clean_text


class QuanbenSite(SiteAdapter):
    site_key = "quanben"
    mirrors = ("https://quanben-xiaoshuo.com",)

    @staticmethod
    def _book_page(url):
        """归一化：目录页 URL -> 书籍页 URL（作者/简介在书籍页）"""
        return re.sub(r"xiaoshuo\.html$", "", url.rstrip("/"))

    def fetch_meta(self, book_url):
        book_url = self._book_page(book_url)
        html = self.http.get(book_url)
        soup = safe_soup(html)
        if soup is None:
            return None
        t = soup.find("title")
        raw_title = t.get_text().strip() if t else ""
        # 标题模式：《书名》- 作者 - 全本小说网
        title, author = "", ""
        m = re.match(r"《([^》]+)》\s*-\s*([^-]+?)\s*-\s*", raw_title)
        if m:
            title, author = m.group(1).strip(), m.group(2).strip()
        else:
            title = raw_title.split(" - ")[0].strip().strip("《》")
        if not title:
            return None
        if not author:
            author_el = soup.find(string=re.compile(r"作者[：:]"))
            if author_el:
                m2 = re.search(r"作者[：:]\s*([^\s<]{1,30})",
                               author_el if isinstance(author_el, str) else author_el.get_text())
                if m2:
                    author = m2.group(1)
        desc = ""
        d = soup.find("meta", attrs={"name": "description"})
        if d:
            desc = d.get("content", "").strip()
        if not desc:
            intro = soup.select_one(".book-intro, .intro, #intro, .description")
            desc = intro.get_text(strip=True)[:500] if intro else ""
        desc = re.sub(r"&nbsp;|简介[:：]", "", desc).strip()
        return BookMeta(title=title, author=author or "未知", description=desc,
                        source_site=self.site_key, source_url=book_url)

    def fetch_chapters(self, book_url):
        # 目录页为 {book}/xiaoshuo.html；用户可能直接传目录页 URL
        if book_url.rstrip("/").endswith("xiaoshuo.html"):
            toc_url = book_url
            book_url = re.sub(r"xiaoshuo\.html$", "", book_url.rstrip("/"))
        elif book_url.endswith("/"):
            toc_url = book_url + "xiaoshuo.html"
        else:
            toc_url = book_url + "/xiaoshuo.html"
        html = self.http.get(toc_url)
        soup = safe_soup(html)
        if soup is None:
            return []
        chapters, seen = [], set()
        for a in soup.find_all("a", href=re.compile(r"/n/[^/]+/\d+\.html")):
            href = a["href"]
            text = a.get_text(strip=True)
            full = self.abs_url(href)
            if full in seen or not text:
                continue
            seen.add(full)
            chapters.append((full, text))
        return chapters

    def fetch_content(self, chapter_url, title=""):
        html = self.http.get(chapter_url, referer=self.base())
        soup = safe_soup(html)
        if soup is None:
            return None
        # 正文：多个长 <p> 段落
        paras = [p.get_text(strip=True) for p in soup.find_all("p")
                 if len(p.get_text(strip=True)) >= 15]
        # 去掉导航类短句已在 clean_text 处理；这里过滤明显的站点推广
        paras = [p for p in paras if not re.search(r"quanben-xiaoshuo|全本小说网|www\.", p)]
        if len(paras) < 3:
            return None
        text = clean_text("\n".join(paras))
        return text or None
