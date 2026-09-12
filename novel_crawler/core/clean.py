# -*- coding: utf-8 -*-
"""正文清洗：导航/推广行剔除 + 广告码/水印清理（静态与渲染两条路径共用）"""
import re

# 水印/广告码清理（自 work_folder/watermark_cleaner + scripts/smart_fix_novel 经验）
_AD_PURE = re.compile(
    r"[a-zA-Z0-9]{1,15}\s*[♀♂◇◆★☆◎⊙¤●＊⊕♟♚♛♜♝♞♟Θ♣♤♥♦♧゛゜ヿヾヽ・]?\s*"
    r"(?:cc|com|net|org|me)\b(?![a-zA-Z0-9])", re.IGNORECASE)
_PRONOUN_MAP = [
    (re.compile(r"\btaxing8\b", re.I), "你"),
    (re.compile(r"\bchunfeng8\b", re.I), "我"),
    (re.compile(r"\bnibiqu\b", re.I), "你"),
    (re.compile(r"\bqg\d+\b"), "他"),
    (re.compile(r"\bbokan9\b", re.I), "我"),
    (re.compile(r"\blewen\d*\b", re.I), "你"),
    (re.compile(r"\bqimao\d*\b", re.I), "他"),
    (re.compile(r"\bqingcang\d+\b", re.I), "我"),
]

# 章节页 UI/导航/推广行（短行才会被剔除）
_SKIP_LINE_PATTERNS = (
    "上一章", "下一章", "章节目录", "目录", "加入书签", "存书签", "投推荐票",
    "新书推荐", "请记住本站", "最快更新", "一秒记住", "天才一秒",
    "本站最新网址", "阅读记录", "手机版", "请收藏本站", "章节报错", "章节错误",
    "关灯", "字号", "夜间", "背景", "滚屏",
)


def clean_watermark(text):
    """广告码清理：纯站名广告删除 + 代词还原"""
    text = _AD_PURE.sub("", text)
    for pat, repl in _PRONOUN_MAP:
        text = pat.sub(repl, text)
    return re.sub(r" {3,}", " ", text)


def clean_lines(text):
    """去除导航/推广短行"""
    out = []
    for line in text.split("\n"):
        s = line.strip()
        if not s:
            continue
        if any(p in s for p in _SKIP_LINE_PATTERNS) and len(s) < 45:
            continue
        out.append(s)
    return "\n".join(out)


def polish(text):
    """统一出口：行清理 + 水印清理 + 压缩空白"""
    if not text:
        return None
    text = re.sub(r"[ \t\u3000]+", " ", text)
    text = clean_lines(text)
    text = clean_watermark(text)
    return text.strip() or None
