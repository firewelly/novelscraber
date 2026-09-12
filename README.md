# novelscraber — 统一小说爬虫 v3.0

> 本仓库为 2025 年 Novel Scraper v9.6 的完全重写版（v3.0）：多站点适配器架构、
> TXT / SQLite 数据库 / 双输出三种模式、书籍元数据（作者/简介/来源URL）、
> 断点续传、多镜像互备、Playwright 渲染。

## 功能特性

- **多站点**：一个适配器架构覆盖 og:novel 元数据站、笔趣阁多镜像家族、SPA 动态站
- **三种输出模式**：`txt`（默认）/ `db`（SQLite）/ `both`（同时），DB 亦可作续传状态源
- **书籍元数据**：书名 / 作者 / 来源(站点+完整URL) / 分类 / 状态 / 更新时间 / 简介 / 抓取时间
- **断点续传**：TXT 用 `\n\n{章节标题}\n\n` 标记定位，DB 用章节表查询，跨次运行自动补缺
- **多镜像互备**：笔趣阁家族 16 个同构镜像，单章失败自动切换兄弟镜像重试
- **进程级浏览器单例**：Playwright 全书共用一个浏览器实例（比逐章启动快 10 倍+）
- **正文清洗**：站点 UI 行剔除、广告码删除、代词还原（taxing8→你 等）

## 安装

```bash
pip install -r requirements.txt
playwright install chromium   # 仅 bqg/xbqk 等渲染站点需要
```

## 用法

```bash
# 按书籍页 URL 下载（域名自动识别站点），默认 txt 模式输出到 ./novels/
python3 crawl.py download --url https://www.xbiquge345.com/book/35247/

# 双输出模式（TXT + SQLite 同时写）
python3 crawl.py download --url "https://quanben-xiaoshuo.com/n/tianmoshentan/xiaoshuo.html" \
    --mode both --db my_novels.db

# 仅数据库模式
python3 crawl.py download --url ... --mode db

# 笔趣阁家族（Playwright 渲染，多镜像）
python3 crawl.py download --site bqg --url "https://www.bqg48.cc/xs/2134/"

# zzxx.org 增量扫描（状态存 zzxx_crawler.db）
python3 crawl.py zzxx                # 增量扫描+下载
python3 crawl.py zzxx --update       # 补新章节 + 旧文件头部元数据升级
python3 crawl.py zzxx --id 72201     # 指定 id 补漏

# 测试与体检
python3 crawl.py download --url ... --limit 3    # 只下前 3 章试水
python3 crawl.py check-sites                     # 全站可用性体检
```

通用选项：`--output DIR`（默认 `./novels`）、`--proxy socks5://127.0.0.1:1080`、`--mode txt|db|both`。

## TXT 输出格式（v3 头部 + 章节）

```
天魔神谭
作者：手枪
来源：xbiquge345 https://www.xbiquge345.com/book/35247/
分类：玄幻魔法
状态：连载中
更新时间：2026-02-25 16:17:11
简介：……
抓取时间：2026-09-12 09:24:45


第一部 第一章 没出息的亚文

（正文……）
```

## 数据库模式（SQLite）

```
novels   : id, title, author, category, status, update_time, description,
           source_site, source_url, chapter_count, crawl_time   UNIQUE(title, source_site)
chapters : id, novel_id→novels, chapter_index, title, content, url   UNIQUE(novel_id, chapter_index)
```

`--mode db/both` 时默认写 `novels.db`（`--db` 可改路径）。续传时自动合并 DB 已有章节，
不会丢章；`--mode both` 时 TXT 与 DB 内容保持一致。

## 站点支持（2026-09-12 实测）

| key | 站点 | 方式 | 元数据 |
|-----|------|------|--------|
| zzxx | zzxx.org | 静态 | og:novel 完整 |
| kuaizhui | kuaizhui.net | 静态 | og:novel 完整 |
| xbiquge345 | xbiquge345.com | 静态 | og:novel 完整 |
| quanben | quanben-xiaoshuo.com | 静态 | 标题解析 |
| yebiquge | yebiquge.com | 静态 | 部分 |
| bqg | 笔趣阁家族 16 镜像 | Playwright | 书页解析 |
| xbqk | xbqk.cc / bqg504 / bqg930 / bqg329 | Playwright | 页面解析 |

新增站点：继承 `novel_crawler/sites/base.py::SiteAdapter` 实现
`fetch_meta / fetch_chapters / fetch_content`，在 `sites/__init__.py` 登记即可。

## 许可

BSD-3-Clause，见 [LICENSE](LICENSE)。

## 免责声明

本工具仅用于个人学习与已获授权内容的备份。请尊重版权，勿用于商业用途或
传播盗版内容；使用本工具产生的任何法律责任由使用者自行承担。
