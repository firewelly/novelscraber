# -*- coding: utf-8 -*-
"""站点适配器：注册表 + 分发。

适配器两层能力：
- StaticAdapter：requests + BeautifulSoup 静态抓取（快，优先用）
- PlaywrightAdapter：整本用一个浏览器渲染章节（共享 core.render.Renderer）
"""
import logging
import re
from abc import ABC, abstractmethod
from urllib.parse import urljoin

from ..core.http import HttpClient
from ..core.meta import BookMeta
from ..core.txtio import clean_text

log = logging.getLogger("novel_crawler.sites")

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    BeautifulSoup = None


def safe_soup(html):
    if not html or BeautifulSoup is None:
        return None
    for parser in ("html.parser", "lxml", "html5lib"):
        try:
            soup = BeautifulSoup(html, parser)
            if soup is not None:
                return soup
        except Exception:
            continue
    return None


def parse_og_novel(soup):
    """解析 og:novel:* 协议元数据（zzxx/kuaizhui/xbiquge345 等现代模板通用）"""
    def meta(prop):
        el = soup.find("meta", property=prop) if soup else None
        return el.get("content", "").strip() if el else ""
    title = meta("og:novel:book_name") or meta("og:novel:book_title") or meta("og:title")
    return {
        "title": title,
        "author": meta("og:novel:author"),
        "category": meta("og:novel:category"),
        "status": meta("og:novel:status"),
        "update_time": meta("og:novel:update_time"),
        "description": meta("og:description") or meta("description"),
    }


def numeric_sort_key(url):
    m = re.search(r"(\d+)\.html", url)
    return int(m.group(1)) if m else 0


class SiteAdapter(ABC):
    """站点适配器基类。site_key 为站点唯一标识（写入 TXT 来源字段）。"""

    site_key = ""
    mirrors = ()                    # 主站 + 镜像（第一个为主）
    needs_render = False            # 章节正文是否需要 Playwright

    def __init__(self, http=None, renderer=None):
        self.http = http or HttpClient()
        self.renderer = renderer    # PlaywrightAdapter 必须传入

    # ---- 子类实现 ----
    @abstractmethod
    def fetch_meta(self, book_url):
        """抓书籍页，返回 BookMeta（必须含 source_url）"""

    @abstractmethod
    def fetch_chapters(self, book_url):
        """返回章节列表 [(url, title)]（按阅读顺序）"""

    @abstractmethod
    def fetch_content(self, chapter_url, title=""):
        """返回章节正文（已清洗），失败返回 None"""

    # ---- 通用工具 ----
    def base(self):
        return self.mirrors[0].rstrip("/")

    def abs_url(self, href, base=None):
        return href if href.startswith("http") else urljoin((base or self.base()) + "/", href)

    def search(self, keyword):
        """按名搜书，返回 [(book_url, title)]。默认不支持。"""
        raise NotImplementedError(f"{self.site_key} 不支持搜索")
