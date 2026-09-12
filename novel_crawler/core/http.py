# -*- coding: utf-8 -*-
"""HTTP 客户端：限速 + 重试 + UA 轮换（自 zzxx_crawler.HttpClient 泛化）"""
import logging
import random
import time

import requests

log = logging.getLogger("novel_crawler.http")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
]


class HttpClient:
    """串行限速 HTTP 客户端。自动探测编码（gbk 站点兼容）。"""

    def __init__(self, min_delay=0.8, max_delay=1.8, max_retries=3, timeout=15, proxy=None):
        self.session = requests.Session()
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.max_retries = max_retries
        self.timeout = timeout
        self.proxies = {"http": proxy, "https": proxy} if proxy else None
        self._last = 0.0

    def get(self, url, referer=None):
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        if referer:
            headers["Referer"] = referer
        delay = random.uniform(self.min_delay, self.max_delay)
        time.sleep(max(0, delay - (time.time() - self._last)))
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self.session.get(url, headers=headers, timeout=self.timeout,
                                        proxies=self.proxies)
                self._last = time.time()
                if resp.status_code == 200:
                    resp.encoding = resp.apparent_encoding or "utf-8"
                    return resp.text
                log.warning("HTTP %s: %s", resp.status_code, url)
            except Exception as e:
                log.warning("请求失败(%s/%s): %s - %s", attempt, self.max_retries, url, e)
            if attempt < self.max_retries:
                time.sleep(random.uniform(2, 5))
        return None
