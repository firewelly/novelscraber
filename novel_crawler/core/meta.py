# -*- coding: utf-8 -*-
"""书籍元数据与 TXT 头部格式（全站统一，兼容旧格式解析与增量补齐）。

TXT 统一头部格式（2026-09 v3）：
    {书名}
    作者：{author}
    来源：{site_key} {source_url}
    分类：{category}
    状态：{status}
    更新时间：{update_time}
    简介：{description}
    抓取时间：{crawl_time}

章节体（与历史格式一致，保证断点续传跨版本兼容）：
    \\n\\n{章节标题}\\n\\n{正文}\\n

历史格式（v1 zzxx / v2 work_folder）会被 fix_metadata 升级到 v3：
    v1: 来源：zzxx.org (id=12345)          —— 无简介/无完整 URL
    v2: {title}\\n作者：..\\n简介：..        —— 无来源/无更新时间
"""
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime

log = logging.getLogger("novel_crawler.meta")


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class BookMeta:
    title: str = ""
    author: str = ""
    source_site: str = ""       # 站点标识，如 zzxx / kuaizhui
    source_url: str = ""        # 书籍页完整 URL
    category: str = ""
    status: str = ""
    update_time: str = ""
    description: str = ""
    crawl_time: str = field(default_factory=now_str)

    def clean(self):
        """清洗字段：去空白、压成单行（简介多行会被压成一行，避免破坏章节标记结构）"""
        def one(s, limit=2000):
            s = re.sub(r"\s+", " ", (s or "").strip())
            return s[:limit]
        self.title = one(self.title, 120)
        self.author = one(self.author, 80) or "未知"
        self.category = one(self.category, 40)
        self.status = one(self.status, 20)
        self.update_time = one(self.update_time, 30)
        self.description = one(self.description)
        return self

    def render_header(self):
        """渲染 v3 头部（结尾以一个空行收束，章节体紧随其后）"""
        self.clean()
        lines = [self.title, f"作者：{self.author}"]
        if self.source_url:
            lines.append(f"来源：{self.source_site} {self.source_url}".rstrip())
        if self.category:
            lines.append(f"分类：{self.category}")
        if self.status:
            lines.append(f"状态：{self.status}")
        if self.update_time:
            lines.append(f"更新时间：{self.update_time}")
        if self.description:
            lines.append(f"简介：{self.description}")
        lines.append(f"抓取时间：{self.crawl_time}")
        return "\n".join(lines) + "\n\n"


# ===== 头部解析与补齐 =====

_HEADER_KEYS = ("作者", "来源", "分类", "状态", "更新时间", "简介", "抓取时间")


def split_header(text, first_chapter_title=None):
    """把文件内容切成 (头部文本, 章节体文本)。

    优先用首章 marker（\\n\\n{title}\\n\\n）定位；失败时退化为：从头开始
    跳过「标题行 + 已知字段行」，直到第一个空行。
    """
    if first_chapter_title:
        marker = f"\n\n{first_chapter_title}\n\n"
        pos = text.find(marker)
        if pos > 0:
            return text[:pos].rstrip("\n") + "\n", text[pos:]
    lines = text.split("\n")
    i = 1  # 第 0 行视为书名
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            break
        if any(line.startswith(k + "：") or line.startswith(k + ":") for k in _HEADER_KEYS):
            i += 1
            continue
        break
    head = "\n".join(lines[:i]).rstrip("\n") + "\n"
    body = "\n".join(lines[i:])
    return head, body


def parse_header(text):
    """从文件头部解析出 BookMeta（缺失字段为空串）。first line = 书名。"""
    head, _ = split_header(text)
    meta = BookMeta()
    for i, line in enumerate(head.split("\n")):
        line = line.strip()
        if i == 0:
            meta.title = line
            continue
        for key in _HEADER_KEYS:
            if line.startswith(key + "：") or line.startswith(key + ":"):
                val = line.split("：", 1)[-1] if "：" in line else line.split(":", 1)[-1]
                val = val.strip()
                if key == "作者":
                    meta.author = val
                elif key == "来源":
                    # 兼容 v1「来源：zzxx.org (id=123)」与 v3「来源：zzxx https://...」
                    m = re.match(r"(\S+)\s+(https?://\S+)", val)
                    if m:
                        meta.source_site, meta.source_url = m.group(1), m.group(2)
                    else:
                        meta.source_site = val
                elif key == "分类":
                    meta.category = val
                elif key == "状态":
                    meta.status = val
                elif key == "更新时间":
                    meta.update_time = val
                elif key == "简介":
                    meta.description = val
                elif key == "抓取时间":
                    meta.crawl_time = val
                break
    return meta


def header_needs_fix(meta):
    """判断旧头部是否缺 metadata（缺简介或缺完整来源 URL）"""
    return (not meta.description) or (not meta.source_url)


def rebuild(text, meta, first_chapter_title=None):
    """用新头部替换文件头部，章节体原样保留。返回新全文。"""
    _, body = split_header(text, first_chapter_title)
    return meta.render_header() + body.lstrip("\n")
