import requests
from bs4 import BeautifulSoup
import re

# 定义初始URL
url_base = "http://www.yueduba2.cc/1565_1565603/"
# 抓取初始页面
response = requests.get(url_base)
soup = BeautifulSoup(response.content, 'html.parser')

# 找到特定的<meta>标签
meta_tag = soup.find('meta', property='og:title')
# 提取content属性值
sub = meta_tag['content']

# 初始化空字符串
cached_title = ""
fb = sub + '\n'  # 添加换行符，使每个页面的内容分开

# 设置计数器
i = 1

while True:
    # 构建新的URL
    url0 = f"{url_base}{i}.html"
    print(url0)
    page = ""
    try:
        # 尝试获取页面内容
        response = requests.get(url0)
        # 尝试使用UTF-8编码解析
        response.encoding = 'utf-8'
        page = response.text
    except UnicodeDecodeError:
        # 如果UTF-8解析失败，尝试GB18030编码
        try:
            response.encoding = 'gb18030'
            page = response.text
        except Exception as e:
            print(f"无法解析页面 {url0}: {e}")
            break
    except Exception as e:
        print(f"无法访问页面 {url0}: {e}")
        break
    
    # 使用正则表达式匹配内容
    pattern_maintext = r'</div>\s+(.+?)</p><script>'
    maintext = re.search(pattern_maintext, page, re.DOTALL).group(1)
    # 替换 maintext 中的 </p><p> 为换行符
    maintext = maintext.replace('</p><p>', '\n')

    # 使用正则表达式匹配标题
    pattern_title = r'<h1 class="am-text-md am-text-center">(.*?)</h1>'
    chapter_title = re.search(pattern_title, page).group(1)

    if chapter_title == cached_title:
        break  # 如果标题相同，说明已经到了最后一章，跳出循环
    else:    
        fb += chapter_title + '\n' + maintext + '\n'  # 每次添加完页面内容后添加换行符

    if i == 1:
        cached_title = chapter_title
    print(chapter_title, cached_title)
    # print(maintext)

    # 更新计数器
    i += 1

# 将收集到的所有内容覆盖写入到sub为文件名的txt文件中
with open(sub + '.txt', 'w', encoding='gb18030') as file:
    file.write(fb)