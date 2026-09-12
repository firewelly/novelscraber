# -*- coding: utf-8 -*-
"""TXT 章节体 IO：章节标记、断点检测、文件重排写入。"""
import logging
import os
import re

log = logging.getLogger("novel_crawler.txtio")

MIN_CHAPTER_CHARS = 100


def chapter_marker(title):
    """章节分隔标记（全项目历史统一格式，勿改）"""
    return f"\n\n{title}\n\n"


def clean_text(text):
    """统一换行、去空行、去非法 surrogate"""
    text = text.replace("\xa0", " ").replace("&nbsp;", " ")
    lines = [l.strip() for l in text.split("\n")]
    text = "\n".join(l for l in lines if l)
    text = text.encode("utf-8", "ignore").decode("utf-8", "ignore")
    return text.strip()


def existing_titles(fp, chapters):
    """断点检测：返回已有章节 title 集合（按 marker 精确匹配）"""
    if not os.path.exists(fp):
        return set()
    try:
        with open(fp, encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except OSError as e:
        log.warning("读取失败 %s: %s", fp, e)
        return set()
    return {t for _, t in chapters if f"\n\n{t}\n\n" in text}


def write_book(fp, meta, chapters, contents):
    """按章节顺序重写完整文件（重排；缺失章节不写占位，留给续传）。

    contents: {title: 正文文本}
    """
    os.makedirs(os.path.dirname(os.path.abspath(fp)), exist_ok=True)
    with open(fp, "w", encoding="utf-8", errors="ignore") as f:
        f.write(meta.render_header())
        for _, title in chapters:
            if title in contents:
                f.write(chapter_marker(title) + contents[title] + "\n")


def safe_filename(title):
    return re.sub(r'[\\/:*?"<>|]', "", (title or "").strip()) or "未命名"
