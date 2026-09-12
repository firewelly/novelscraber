# -*- coding: utf-8 -*-
"""站点注册表与分发。新增站点：实现 SiteAdapter 后在 SITES 登记即可。"""
import logging
from urllib.parse import urlparse

from .base import SiteAdapter
from .ogstatic import OgStaticSite
from .quanben import QuanbenSite
from .bqg48 import Bqg48Family
from .spa import SpaSite
from .zzxx import ZzxxSite

log = logging.getLogger("novel_crawler.sites")


# ---- 静态 og:novel 站点实例化 ----
def _make_ogstatic(key, mirrors, content_selector, chapter_scope=None):
    return type("Site_" + key, (OgStaticSite,), {
        "site_key": key,
        "mirrors": tuple(mirrors),
        "content_selector": tuple(content_selector),
        "chapter_scope": chapter_scope,
    })


KuaizhuiSite = _make_ogstatic(
    "kuaizhui", ["https://www.kuaizhui.net"],
    [".content", "#content", ".read_bg .content"],
)
Xbiquge345Site = _make_ogstatic(
    "xbiquge345", ["https://www.xbiquge345.com"],
    ["#content", ".showtxt", "#chaptercontent"],
)
YebiqugeSite = _make_ogstatic(
    "yebiquge", ["https://www.yebiquge.com"],
    ["#content", "#htmlContent", ".showtxt"],
)

# ---- 笔趣阁多镜像家族（同构模板，2026-09-12 批量验证存活）----
BqgMirrors = [
    "https://www.bqg48.cc", "https://www.bqg72.net", "https://www.3bqg.cc",
    "https://www.bqg099.cc", "https://www.bqg129.cc", "https://www.bqgbb.cc",
    "https://www.bqgbl.com", "https://www.bqgcom.com", "https://www.bqged.cc",
    "https://www.biqu21.cc", "https://www.xinbiquge.com", "https://www.xinbiquge.net",
    "https://www.ibiquw.com", "https://www.ouxsw.com", "https://www.x23su.com",
    "https://www.bq555.cc",
]

# ---- 注册表：site_key -> 类 ----
SITES = {
    "zzxx": ZzxxSite,
    "kuaizhui": KuaizhuiSite,
    "xbiquge345": Xbiquge345Site,
    "yebiquge": YebiqugeSite,
    "quanben": QuanbenSite,
    "bqg": Bqg48Family,          # 笔趣阁家族；mirrors 见 BqgMirrors
    "xbqk": SpaSite,             # SPA 家族：xbqk/bqg504/bqg930/bqg329
}

# 域名 -> site_key（download --url 自动分发用）
_DOMAIN_MAP = {}
for _key, _cls in SITES.items():
    _mirrors = BqgMirrors if _key == "bqg" else _cls.mirrors
    if _key == "xbqk":
        _mirrors = ("https://www.xbqk.cc", "https://www.bqg504.cc",
                    "https://www.bqg930.cc", "https://www.bqg329.cc")
    for _m in _mirrors:
        _DOMAIN_MAP[urlparse(_m).netloc.replace("www.", "")] = _key
_DOMAIN_MAP.update({
    "bqg504.cc": "xbqk", "bqg930.cc": "xbqk", "bqg329.cc": "xbqk",
})


def resolve_site_key(url):
    """按域名识别站点 key"""
    host = urlparse(url).netloc.replace("www.", "")
    return _DOMAIN_MAP.get(host)


def make_site(key, http=None, renderer=None):
    cls = SITES.get(key)
    if cls is None:
        raise KeyError(f"未知站点: {key}（可选: {', '.join(SITES)}）")
    if cls.needs_render and renderer is None:
        raise ValueError(f"站点 {key} 需要 Playwright 渲染器（Renderer）")
    if key == "bqg":
        return _make_bqg(http, renderer)
    return cls(http=http, renderer=renderer)


def _make_bqg(http, renderer):
    cls = SITES["bqg"]
    inst = cls.__new__(cls)
    SiteAdapter.__init__(inst, http=http, renderer=renderer)
    inst.site_key = "bqg"
    inst.mirrors = tuple(BqgMirrors)
    return inst


def all_sites_report(http=None):
    """站点可用性体检：每个主镜像 HTTP 探测"""
    if http is None:
        http = HttpClient()
    rows = []
    targets = [("zzxx", ZzxxSite.mirrors[0])]
    for key, cls in SITES.items():
        if key in ("zzxx", "bqg"):
            continue
        targets.append((key, cls.mirrors[0]))
    targets += [("bqg:" + m, m) for m in BqgMirrors]
    for key, base in targets:
        txt = http.get(base + "/", )
        rows.append((key, base, "OK" if txt else "FAIL"))
        log.info("%-22s %s %s", key, base, rows[-1][2])
    return rows
