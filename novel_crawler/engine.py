# -*- coding: utf-8 -*-
"""下载引擎：整本书下载（metadata 头部 + 断点续传 + 章节重排 + 失败重试）"""
import logging
import os
import time

from .core.meta import BookMeta, parse_header, header_needs_fix, rebuild
from .core.txtio import (chapter_marker, existing_titles, safe_filename,
                         write_book, MIN_CHAPTER_CHARS)
from .sites import make_site, resolve_site_key

log = logging.getLogger("novel_crawler.engine")


class Downloader:
    """输出模式（mode）：txt / db / both。db 模式写入 SQLite（novels+chapters 两表）。"""

    def __init__(self, output_dir, renderer=None, proxy=None, test_mode=False,
                 max_fail_ratio=0.5, mode="txt", db_path=None):
        self.output_dir = os.path.abspath(output_dir)
        self.renderer = renderer
        self.proxy = proxy
        self.test_mode = test_mode
        self.max_fail_ratio = max_fail_ratio   # 失败章节超此比例则不写文件（防半残书覆盖好书）
        self.mode = mode if mode in ("txt", "db", "both") else "txt"
        self.db_path = os.path.abspath(db_path) if db_path else \
            os.path.join(self.output_dir, "novels.db")
        os.makedirs(self.output_dir, exist_ok=True)

    def _site(self, key):
        from .core.http import HttpClient
        http = HttpClient(proxy=self.proxy)
        return make_site(key, http=http, renderer=self.renderer)

    def _open_db(self):
        from .core.dbout import NovelDB
        return NovelDB(self.db_path)

    def resolve(self, url):
        """URL -> site_key（按域名自动识别）"""
        key = resolve_site_key(url)
        if not key:
            raise SystemExit(f"无法识别站点域名: {url}\n已知站点见 crawl.py --list-sites")
        return key

    def download(self, url, site_key=None, limit=None):
        """下载整本书。返回 (file_path_or_db, 下载章节数)"""
        key = site_key or self.resolve(url)
        site = self._site(key)
        t0 = time.time()
        log.info("[%s] 抓取书籍信息: %s", key, url)
        meta = site.fetch_meta(url)
        if not meta:
            raise SystemExit(f"书籍信息获取失败: {url}")
        chapters = site.fetch_chapters(url)
        if not chapters:
            raise SystemExit(f"章节列表为空: {url}")
        log.info("《%s》%s | %d 章", meta.title, meta.author, len(chapters))

        urls = {t: u for u, t in chapters}
        fp = os.path.join(self.output_dir, safe_filename(meta.title) + ".txt")
        db = self._open_db() if self.mode in ("db", "both") else None
        try:
            # 续传源：TXT 标记 + DB 章节表（按模式取并集）
            have = existing_titles(fp, chapters) if self.mode in ("txt", "both") else set()
            if db:
                _, db_have = db.existing_titles(meta.title, meta.source_site,
                                                [t for _, t in chapters])
                have |= db_have
            missing = [(u, t) for u, t in chapters if t not in have]
            log.info("已有 %d 章，待下载 %d 章", len(have), len(missing))
            if not missing:
                self._maybe_fix_header(fp, meta, chapters)
                return fp, 0
            if limit:
                missing = missing[:limit]
            elif self.test_mode:
                missing = missing[:3]

            contents, failed = {}, []
            for i, (u, t) in enumerate(missing, 1):
                text = site.fetch_content(u, title=t)
                if text and len(text) >= MIN_CHAPTER_CHARS:
                    contents[t] = text
                else:
                    failed.append(t)
                if i % 10 == 0 or i == len(missing):
                    log.info("进度 %d/%d（成功 %d，失败 %d）", i, len(missing), len(contents), len(failed))

            fail_ratio = len(failed) / len(missing) if missing else 0
            if fail_ratio > self.max_fail_ratio and not self.test_mode:
                log.error("失败率 %.0f%% 过高，不写入（保留原状）", fail_ratio * 100)
                return fp, 0
            meta.crawl_time = meta.crawl_time or time.strftime("%Y-%m-%d %H:%M:%S")

            n_new = len(contents)
            if self.mode in ("txt", "both"):
                # 合并旧文件已有章节 + 新下载，按目录顺序重写
                all_contents = self._load_existing_contents(fp, chapters)
                all_contents.update(contents)
                write_book(fp, meta, chapters, all_contents)
                log.info("TXT 写入: %s", fp)
            if db:
                nid = db.upsert_novel(meta, len(chapters))
                # 回读 DB 已有章节，合并新下载后再重写（防丢已入库章节）
                merged = db.load_contents(nid)
                merged.update(contents)
                n_db = db.replace_chapters(nid, chapters, merged, urls)
                t, c = db.stats()
                log.info("DB 写入: %s（库内 %s 本 / %s 章）", self.db_path, t, c)
            log.info("《%s》完成（本次 %d 章，失败 %d 章，耗时 %.0fs）",
                     meta.title, n_new, len(failed), time.time() - t0)
            if failed and not self.test_mode:
                log.info("失败章节将在下次运行时自动续传")
            return fp, n_new
        finally:
            if db:
                db.close()

    def _load_existing_contents(self, fp, chapters):
        """从旧文件中恢复已有章节内容（按 marker 切分）"""
        result = {}
        if not os.path.exists(fp):
            return result
        with open(fp, encoding="utf-8", errors="ignore") as f:
            text = f.read()
        located = []
        for _, t in chapters:
            marker = chapter_marker(t)
            pos = text.find(marker)
            if pos >= 0:
                located.append((pos, marker, t))
        located.sort()
        for i, (pos, marker, t) in enumerate(located):
            end = located[i + 1][0] if i + 1 < len(located) else len(text)
            content = text[pos + len(marker):end].strip()
            if content and not content.startswith("[章节"):
                result[t] = content
        return result

    def _maybe_fix_header(self, fp, meta, chapters):
        """文件已全量下载时，顺带检查旧头部是否缺 metadata"""
        if not os.path.exists(fp):
            return
        with open(fp, encoding="utf-8", errors="ignore") as f:
            text = f.read()
        old = parse_header(text)
        if not header_needs_fix(old):
            return
        meta.description = meta.description or old.description
        meta.author = meta.author or old.author
        first_title = chapters[0][1] if chapters else None
        with open(fp, "w", encoding="utf-8", errors="ignore") as f:
            f.write(rebuild(text, meta, first_title))
        log.info("《%s》头部已升级到 v3（补齐简介/来源URL）", meta.title)

    def fix_metadata(self, site_key, file_path):
        """对单个旧 TXT 做头部 metadata 补齐（按来源站点重新抓书页）"""
        key = site_key or self.resolve_file(file_path)
        if key == "zzxx":
            site = self._site("zzxx")
            return site.fix_file_metadata(file_path)
        site = self._site(key)
        with open(file_path, encoding="utf-8", errors="ignore") as f:
            text = f.read()
        old = parse_header(text)
        if not old.source_url:
            log.warning("%s 头部无来源 URL，无法自动补齐（请用 --url 指定书籍页）", file_path)
            return False
        meta = site.fetch_meta(old.source_url)
        if not meta:
            log.warning("%s 源页面不可访问", old.source_url)
            return False
        meta.title = meta.title or old.title
        meta.author = meta.author or old.author or "未知"
        chapters = site.fetch_chapters(old.source_url)
        first_title = chapters[0][1] if chapters else None
        with open(file_path, "w", encoding="utf-8", errors="ignore") as f:
            f.write(rebuild(text, meta, first_title))
        log.info("%s 头部已补齐", file_path)
        return True

    def resolve_file(self, fp):
        """从文件头部来源字段识别站点"""
        with open(fp, encoding="utf-8", errors="ignore") as f:
            head = f.read(2000)
        old = parse_header(head)
        if old.source_site:
            return old.source_site.split()[0]
        raise SystemExit(f"{fp} 头部无来源信息，请用 --site 指定")
