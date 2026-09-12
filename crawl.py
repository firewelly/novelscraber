#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""novel_crawler 统一 CLI。

用法（在项目根目录）：
    python3 src/crawl.py download --url https://www.xbiquge345.com/book/35247/
    python3 src/crawl.py download --site kuaizhui --url https://www.kuaizhui.net/tmst/ --limit 5
    python3 src/crawl.py download --site bqg --url https://www.bqg48.cc/xs/2134/   # Playwright 渲染
    python3 src/crawl.py zzxx --test            # zzxx 增量扫描+下载（沿 scrapers/zzxx_crawler.db 状态）
    python3 src/crawl.py zzxx --update          # zzxx 已下载书籍更新 + 头部 metadata 补齐
    python3 src/crawl.py fix-meta --site zzxx --file "novels/某书.txt"
    python3 src/crawl.py check-sites            # 全站可用性体检
"""
import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from novel_crawler.core.render import Renderer            # noqa: E402
from novel_crawler.engine import Downloader               # noqa: E402
from novel_crawler.sites import make_site, all_sites_report, SITES  # noqa: E402

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 默认输出 = 当前工作目录下的 novels/（项目内从根目录运行即写入根 novels/；
# 独立发行版在仓库目录运行则写入仓库 novels/）
DEFAULT_OUTPUT = os.path.abspath("novels")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("crawl")


def main():
    ap = argparse.ArgumentParser(description="统一小说爬虫（工程化版 v10）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_dl = sub.add_parser("download", help="按书籍页 URL 下载整本")
    p_dl.add_argument("--url", required=True, help="书籍页 URL（按域名自动识别站点）")
    p_dl.add_argument("--site", help="强制指定站点 key（默认按域名识别）")
    p_dl.add_argument("--output", default=DEFAULT_OUTPUT)
    p_dl.add_argument("--limit", type=int, help="只下载前 N 个缺失章节（测试）")
    p_dl.add_argument("--proxy", help="代理，如 socks5://127.0.0.1:1080")
    p_dl.add_argument("--mode", choices=["txt", "db", "both"], default="txt",
                      help="输出模式：txt / 数据库 / 双输出（默认 txt）")
    p_dl.add_argument("--db", help="数据库路径（默认 <output>/novels.db；--mode db/both 时生效）")

    p_zz = sub.add_parser("zzxx", help="zzxx.org 增量扫描/更新/补漏")
    p_zz.add_argument("--rescan", action="store_true")
    p_zz.add_argument("--scan-only", action="store_true")
    p_zz.add_argument("--update", action="store_true", help="补新章节 + 升级旧文件头部 metadata")
    p_zz.add_argument("--id", type=int, help="指定书籍 id 下载")
    p_zz.add_argument("--test", action="store_true")
    p_zz.add_argument("--output", default=DEFAULT_OUTPUT)
    p_zz.add_argument("--proxy", help="代理")

    p_fix = sub.add_parser("fix-meta", help="旧 TXT 头部 metadata 补齐（简介/来源URL）")
    p_fix.add_argument("--file", required=True)
    p_fix.add_argument("--site", help="站点 key（头部有来源时可省略）")

    p_chk = sub.add_parser("check-sites", help="全站可用性体检")
    p_chk.add_argument("--proxy")

    args = ap.parse_args()

    needs_render = args.cmd in ("download",) and (
        (args.site == "bqg") or (args.site == "xbqk") or
        (not args.site and any(d in args.url for d in (
            "bqg48", "bqg72", "3bqg", "bqg099", "bqg129", "bqgbb", "bqgbl",
            "bqgcom", "bqged", "biqu21", "xinbiquge", "ibiquw", "ouxsw",
            "x23su", "bq555", "xbqk"))))
    renderer = None
    if needs_render:
        log.info("启动 Playwright 渲染器（本进程共用一个浏览器实例）")
        renderer = Renderer(proxy=args.proxy).__enter__()

    if args.cmd == "download":
        dl = Downloader(args.output, renderer=renderer, proxy=args.proxy,
                        mode=args.mode, db_path=args.db)
        fp, n = dl.download(args.url, site_key=args.site, limit=args.limit)
        print(f"完成: {fp}（本次 {n} 章）")

    elif args.cmd == "zzxx":
        from novel_crawler.core.http import HttpClient
        from novel_crawler.sites.zzxx import ZzxxSite
        site = ZzxxSite(http=HttpClient(proxy=args.proxy))
        zzxx_run(site, args)

    elif args.cmd == "fix-meta":
        dl = Downloader(DEFAULT_OUTPUT)
        dl.fix_metadata(args.site, args.file)

    elif args.cmd == "check-sites":
        from novel_crawler.core.http import HttpClient
        rows = all_sites_report(HttpClient(proxy=args.proxy))
        ok = sum(1 for _, _, s in rows if s == "OK")
        print(f"\n可用 {ok}/{len(rows)}")

    if renderer:
        try:
            renderer.__exit__(None, None, None)
        except Exception:
            pass


def zzxx_run(site, args):
    """zzxx 增量模式（移植自 zzxx_crawler.main，头部用 v3 metadata 格式）"""
    from novel_crawler.core.http import HttpClient  # noqa: F401
    from novel_crawler.core.meta import header_needs_fix, parse_header
    from novel_crawler.core.txtio import existing_titles, safe_filename, write_book

    state = site._State()
    st = state.state()
    out = args.output
    log.info("zzxx 状态: last_scanned_id=%s", st["last_scanned_id"])

    def dl_book(bid, meta):
        chapters = site.fetch_chapters(site.book_url(bid))
        if not chapters:
            log.warning("[%s]《%s》无章节", bid, meta.title)
            return 0
        fp = os.path.join(out, safe_filename(meta.title) + ".txt")
        have = existing_titles(fp, chapters)
        missing = [(u, t) for u, t in chapters if t not in have]
        log.info("[%s]《%s》共%d章 已有%d 待下%d", bid, meta.title, len(chapters), len(have), len(missing))
        if not missing:
            # 全量已有 → 补头部
            with open(fp, encoding="utf-8", errors="ignore") as f:
                text = f.read()
            if header_needs_fix(parse_header(text)):
                site.fix_file_metadata(fp, {"id": bid})
            return 0
        if args.test:
            missing = missing[:3]
        contents = {}
        for u, t in missing:
            c = site.fetch_content(u, title=t)
            if c:
                contents[t] = c
        write_book(fp, meta, chapters, contents)
        return len(contents)

    if args.id:
        meta = site.probe(args.id)
        if not meta:
            raise SystemExit(f"id={args.id} 不存在")
        dl_book(args.id, meta)
        return

    if args.update:
        fixed = 0
        for row in state.downloaded_rows():
            bid = row["id"]
            meta = site.probe(bid)
            if not meta:
                log.warning("[%s]《%s》不可访问", bid, row["title"])
                continue
            meta.description = meta.description or (row["description"] or "")
            n = dl_book(bid, meta)
            if n and not args.test:
                fixed += 1
            if args.test:
                break
        log.info("更新完成: %s 本", fixed)
        return

    # 扫描模式
    if args.rescan:
        hp_max, scan_start = 200000, 1
    else:
        hp_max = site.homepage_max_id() or st["last_homepage_max_id"] or 200000
        scan_start = st["last_scanned_id"] + 1
    log.info("扫描范围 [%d, %d]", scan_start, hp_max)
    found = downloaded = 0
    for bid in range(scan_start, hp_max + 1):
        meta = site.probe(bid)
        last = bid
        if meta:
            found += 1
            from novel_crawler.core.txtio import safe_filename
            fp = os.path.join(out, safe_filename(meta.title) + ".txt")
            if os.path.exists(fp):
                log.info("[%s]《%s》已存在，跳过", bid, meta.title)
            elif args.scan_only:
                log.info("[%s]《%s》(%s) [仅扫描]", bid, meta.title, meta.author)
            else:
                dl_book(bid, meta)
                downloaded += 1
        state.update(last_scanned_id=last, last_homepage_max_id=hp_max,
                     total_found=found, total_downloaded=downloaded)
        if args.test and bid >= scan_start + 2:
            break
    log.info("完成：发现 %d，下载 %d", found, downloaded)


if __name__ == "__main__":
    main()
