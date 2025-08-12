# Novel Scraper

一个用于从各种小说网站抓取小说内容的Python工具集。

## 功能特性

- 支持多个小说网站的内容抓取
- **并行化下载**：支持多线程同时下载多部小说，大幅提升下载速度
- 自动重试机制，处理网络错误
- 支持批量下载多部小说
- 自动文件整理功能
- 支持多种编码格式（UTF-8和GB18030自动识别）
- 命令行参数支持，可自定义输入文件和线程数

## 支持的网站

- www.yueduba2.cc（专门优化）
- www.ibiquges.org
- www.lwma.cc
- www.bqg228.com
- www.biquzw.la
- www.bqlo.cc
- www.paozww.com
- www.zzxx.org
- www.zxxs123.com
- www.qqxsnew.com
- www.xiushukong.com
- www.biqusa.com
- www.biqudu.net
- www.xbiquwx.la
- www.biqufan.com
- www.biquwx.la
- 以及更多...

## 安装

1. 克隆此仓库：
```bash
git clone https://github.com/your-username/novelscraper.git
cd novelscraper
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

## 使用方法

### 批量下载小说

1. 创建一个名为 `download_list10.txt` 的文件，每行包含一个小说的URL
2. 运行批量下载脚本：

**基本用法：**
```bash
python novel_scraper.py
```

**高级用法（自定义参数）：**
```bash
# 指定输入文件和线程数
python novel_scraper.py -i my_novel_list.txt -t 16

# 或使用完整参数名
python novel_scraper.py --input_file my_novel_list.txt --max_workers 16
```

**参数说明：**
- `-i, --input_file`: 指定输入文件名（默认：download_list10.txt）
- `-t, --max_workers`: 指定最大线程数（默认：8）

### 下载单部小说

使用 `single_novel_scraper.py` 下载单部小说：
```bash
python single_novel_scraper.py
```

注意：需要在脚本中修改 `url_base` 变量为目标小说的URL。

### 文件整理

下载完成后，使用清理脚本整理文件：
```bash
python clean.py
```

这将把所有下载的txt文件移动到 `novels` 文件夹中。

## 文件说明

- `novel_scraper.py`: 主要的批量下载脚本（基于dl9.6并行化版本）
- `single_novel_scraper.py`: 单部小说下载脚本
- `clean.py`: 文件整理工具
- `requirements.txt`: Python依赖包列表
- `download_list10.txt`: 下载列表文件（需要用户创建）

## 注意事项

1. 请遵守网站的robots.txt和使用条款
2. 建议在使用时设置适当的延迟，避免对服务器造成过大压力
3. 仅供学习和个人使用，请勿用于商业用途
4. 下载的内容请遵守相关版权法律法规

## 版本历史

- **v9.6**: 引入并行化下载功能，支持多线程同时下载，大幅提升下载速度
- v9.5: 专门优化 www.yueduba2.cc 网站的下载流程
- v9.4.1: 测试支持 www.bqlo.cc
- v9.4p: 启用UTF-8和GB18030自动识别，适配更多网站
- v9.3p: 添加命令行参数支持，可自定义输入文件和最大线程数
- v9.2p: 优化输出格式，显示书名而非章节名
- v9.1p: 尝试引入并行化功能
- v9.1: 适配 www.ibiquges.org
- v9: 适配 www.lwma.cc 并清理代码
- v8c: 修复503错误的性能问题
- v8B: 适配 www.bqg228.com
- v8A: 适配多个新网站

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 贡献

欢迎提交问题和拉取请求来改进这个项目。