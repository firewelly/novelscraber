---
name: novel-crawler
display_name: 小说爬虫
display_name_en: Novel Crawler
description: 当用户需要从小说网站下载整本小说为 TXT 文件、查询支持哪些小说站、或给已有 TXT 补下载缺失章节时使用。多站点适配（zzxx/xbiquge345/kuaizhui/quanben/笔趣阁镜像家族），断点续传，输出含书名/作者/简介/来源URL的元数据头部。仅限个人学习与授权内容备份。
category: Tools
description_zh: 多站点小说爬虫——整本下载为带元数据头部的 TXT，断点续传，多镜像互备
description_en: Multi-site novel crawler — download full books as metadata-rich TXT with resume support
version: 10.0.0
author: firewell
---

# 小说爬虫 Skill（novelscraber v3）

将小说网站的书以 **TXT 文件**（含元数据头部）整本下载到本地。断点续传：重跑自动跳过已有章节，只补缺失章节。

## 前置条件

```bash
# 仓库根目录即本 skill 所在目录的上级（crawl.py 与 novel_crawler/ 在那里）
pip install requests beautifulsoup4 lxml
# 仅下载笔趣阁家族（--site bqg）或 xbqk SPA 站时需要：
pip install "playwright>=1.40" && playwright install chromium
```

## 支持的站点（2026-09 实测）

| 域名 | site key | 方式 | 说明 |
|------|----------|------|------|
| zzxx.org | zzxx | 静态 | 元数据完整 |
| xbiquge345.com | xbiquge345 | 静态 | 元数据完整，正文量大 |
| kuaizhui.net | kuaizhui | 静态 | 元数据完整 |
| quanben-xiaoshuo.com | quanben | 静态 | 可传目录页或书籍页 URL |
| yebiquge.com | yebiquge | 静态 | |
| bqg48.cc 等 16 个笔趣阁镜像 | bqg | Playwright | 单章失败自动换镜像 |
| xbqk.cc / bqg504 / bqg930 / bqg329 | xbqk | Playwright | SPA 站 |

其他/未知域名 → 提示不支持，不要猜测站点。

## 标准工作流（TXT 模式，默认）

```bash
cd <仓库根目录>   # 即 crawl.py 所在目录

# 1. 下载整本（URL 为书籍页/目录页地址；按域名自动识别站点）
python3 crawl.py download --url "https://www.xbiquge345.com/book/35247/"

# 2. 试水：先只下 3 章确认站点可用与正文质量，再全量
python3 crawl.py download --url "<书籍页URL>" --limit 3

# 3. 补下载缺失章节：同一命令重跑即可（自动断点续传）
python3 crawl.py download --url "<书籍页URL>"

# 笔趣阁家族需要渲染器（自动启动，无需额外参数）
python3 crawl.py download --site bqg --url "https://www.bqg48.cc/xs/2134/"
```

输出：`./novels/{书名}.txt`（`--output DIR` 可改）。

## TXT 输出格式

```
{书名}
作者：{author}
来源：{站点} {书籍页URL}
分类：{category}
状态：{status}
更新时间：{update_time}
简介：{description}
抓取时间：{timestamp}


{第一章标题}

{正文}

{第二章标题}

（……）
```

章节边界为 `\n\n{章节标题}\n\n`，续传/去重依赖此标记，不要修改文件内的章节标题行。

## 其他模式（按需）

```bash
--mode db          # 写 SQLite（novels + chapters 两表），不生成 TXT
--mode both        # TXT 与 SQLite 同时输出
--db path/to.db    # 指定库文件（默认 novels/novels.db）
--output DIR       # 输出目录（默认 ./novels）
--proxy socks5://127.0.0.1:1080   # 站点连不上时用代理

# zzxx.org 增量扫描（按 id 递增发现新书）
python3 crawl.py zzxx              # 增量扫描+下载
python3 crawl.py zzxx --update     # 补新章节 + 旧文件头部元数据升级
python3 crawl.py zzxx --test       # 每本只下 3 章

# 旧 TXT 头部缺作者/简介/来源时补齐
python3 crawl.py fix-meta --site zzxx --file "novels/某书.txt"

# 全站可用性体检
python3 crawl.py check-sites
```

## 故障处理

| 现象 | 处置 |
|------|------|
| 书籍信息获取失败 | URL 是否为书籍页/目录页；站点是否已死亡（对照 check-sites） |
| 失败率 >50% 不写文件 | 站点反爬加重，稍后重试或用 --proxy；已下载章节不丢失 |
| 章节内容为空 | 该章在站点上缺失，重跑会自动重试 |
| Playwright 超时 | 仅 bqg/xbqk 需要；重试，或先 `playwright install chromium` |

## 合规边界

仅用于个人学习与已获授权内容的备份。不得分发爬取的内容，不得用于商业用途。
未知/未收录站点不要尝试自行编写适配器（除非用户明确要求并自行承担合规责任）。
