# -*- coding: utf-8 -*-
"""Playwright 渲染器。

对比 v2_2 的关键改进：整个进程只启动一次浏览器（v2_2 每章重启一次，慢 10 倍+），
通用正文提取（选择器候选 + 最大中文块兜底），内置广告码/水印清理。
"""
import logging

from .clean import clean_lines, clean_watermark, polish

log = logging.getLogger("novel_crawler.render")

# 正文容器候选（按优先级；覆盖已验证站点：bqg48=.word_read、通用=#content 等）
CONTENT_SELECTORS = [
    "#htmlContent", "#chaptercontent", "#content", "#txt", "#nr1", "#nr",
    ".word_read", ".showtxt", ".read-content", ".txtnav", "#booktxt",
    "#acontent", ".readcotent", ".article-content",
]

# 章节页占位/反爬特征：出现即视为无正文
PLACEHOLDER_PATTERNS = (
    "章节错误", "章节内容缺失", "内容加载失败", "请安装", "正在加载",
)


class Renderer:
    """进程级单例 Playwright 渲染器（with Renderer(proxy=...) as r: r.page(...)）"""

    def __init__(self, headless=True, proxy=None):
        self.headless = headless
        self.proxy = proxy
        self._pw = None
        self._browser = None
        self._context = None
        self._page = None

    def __enter__(self):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        launch_kw = {"headless": self.headless}
        if self.proxy:
            launch_kw["proxy"] = {"server": self.proxy}
        self._browser = self._pw.chromium.launch(**launch_kw)
        self._context = self._browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
        self._page = self._context.new_page()
        return self

    def __exit__(self, *exc):
        for obj in (self._context, self._browser):
            try:
                if obj:
                    obj.close()
            except Exception:
                pass
        try:
            if self._pw:
                self._pw.stop()
        except Exception:
            pass

    def goto(self, url, wait_ms=2500, timeout=40000):
        """导航并等待渲染，返回 page（失败抛异常）"""
        page = self._page
        page.goto(url, timeout=timeout, wait_until="domcontentloaded")
        page.wait_for_timeout(wait_ms)
        return page

    def extract_content(self, url, wait_ms=2500):
        """渲染章节页并提取正文。返回清洗后的文本或 None（占位/失败）。"""
        try:
            page = self.goto(url, wait_ms=wait_ms)
        except Exception as e:
            log.warning("渲染失败 %s: %s", url, type(e).__name__)
            return None
        # 1) 选择器候选
        for sel in CONTENT_SELECTORS:
            try:
                el = page.query_selector(sel)
                if el:
                    text = el.inner_text()
                    if text and len(text.strip()) > 100:
                        return self._finish(text)
            except Exception:
                continue
        # 2) 兜底：最大中文文本块
        text = page.evaluate("""() => {
            let best = '';
            document.querySelectorAll('div,article,dd,td').forEach(el => {
                if (el.children.length > 8) return;
                const t = el.innerText || '';
                const cn = (t.match(/[\\u4e00-\\u9fff]/g) || []).length;
                if (cn > 300 && t.length > best.length) best = t;
            });
            return best;
        }""")
        if text and len(text.strip()) > 100:
            return self._finish(text)
        log.warning("无有效正文: %s", url)
        return None

    @staticmethod
    def _finish(text):
        # 占位行由 polish 剔除；真占位页清理后为空 → 返回 None
        return polish(text)
