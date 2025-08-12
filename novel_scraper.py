# v9.6 introduce clean_text() function.     
#       清理 HTML 标签：确保最终输出的文本不包含任何 HTML 标签。
#       规范化换行符：避免文本中出现多余的空白行，使输出更整洁。
#       模块化设计：clean_text 函数可以复用于其他需要清理文本的地方。
# v9.5 major update; add a new function specially for http://www.yueduba2.cc; 把原始的download_novel()函数改名为download_novel_other, 引入了新的函数download_novel_yueduba2_cc(url)，这个函数同时做相当于download_novel_other和get_info功能，但是没有retrying功能；引入新的download_novel(url)作为流程控制，基于网址判定进入那个下载流程，未来在此处扩展别的下载器。      
# v9.4.1 tested on https://www.bqlo.cc/
# v9.4p Enable the auto jusitification on utf8 and gb18030 in the get_info() function. Adopt for https://www.paozww.com/ and https://www.zzxx.org/, clean the adoption to https://www.zxxs123.com/, https://www.qqxsnew.com/ and https://www.xiushukong.com/, https://www.qqxsnew.net/, in content2 and contents3
# v9.3p added the parameters on the input lists and the max_workers
# v9.2p optimize the output as book title rather the chapter title
# v9.1p Try to include the parrelization 
# v9.1 - adapted with https://www.ibiquges.org/
# v9 - adapted with https://www.lwma.cc/ and clean the codes from v8C1
# v8c - fixed the performance issue regarding to 503 errors - add better retry in the get_info to fix the 503 error on the server performance; also shorten the retrying wait time. 
# v8B - adjusted for https://www.bqg228.com
# 2023-06-04 Tested also work on https://www.biquzw.la/20_20104/

# v8A - adjusted for https://www.qqxsnew.com/ and https://www.xiushukong.com/, https://www.qqxsnew.net/.  major change in the get_info()
# on 2022-07-22 tested on https://www.biqusa.com
# v8.5 also adapt to https://www.biqudu.net/; in addition to https://www.xbiquwx.la/, https://www.biqufan.com/, and https://www.biquwx.la/
# v8.4 also adapt to https://www.xbiquwx.la/, https://www.biqufan.com/, and https://www.biquwx.la/
# change log: v8.1 - v8.2 import the retry module in the row 8 and row 14 to handle the errors.
# add the adoption to https://www.biquwx.la/ and https://www.biquger.com/


import requests
import re
import time
import random
from retrying import retry
import concurrent.futures
import argparse
from bs4 import BeautifulSoup

def clean_text(text):
    """
    清理文本：移除 HTML 标签并规范化换行符。
    """
    # 移除所有 HTML 标签
    text = re.sub(r'<.*?>', '\n', text)
    # 将连续的换行符替换为单个换行符
    text = re.sub(r'[\r\n]+', '\n', text)
    return text.strip()  # 移除首尾空白字符

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36 Edge/15.15063'
}


@retry(wait_random_min=100, wait_random_max=1500, stop_max_attempt_number=150)
def get_info(url):
    fb = ''
    retry_count = 0
    max_retry = 150
    headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36 Edge/15.15063'
}
    while retry_count < max_retry:
        res = requests.get(url, headers=headers, timeout=60)
        try:
            full_txt = res.content.decode('utf-8')
        except UnicodeDecodeError: 
            full_txt = res.content.decode('gb18030',errors='ignore')
        if res.status_code == 200:
            
            # Modified to better addapt https://www.bgq228.com/
            if (len(fb) < 10):
                contents5 = re.findall(r'\<div id=\"chaptercontent\" class\=\"Readarea ReadAjax\_content\"\>\s*([^\r\n]+)', full_txt, re.S)
                
                for content5 in contents5:
                    txts = re.split(r'<br /><br />', content5)
                    for txt in txts:
                        fb = fb + txt + '\n' 
            # added in v9.4p to adapt https://www.zzxx.org/
            if (len(fb) < 10):
                contents6 = re.findall(r'\<div id\=\"htmlContent\"\>\<p\>(.+?)\<\/p\>', full_txt, re.S)
                
                for content6 in contents6:
                    txts = re.split(r'<br>', content6)
                    for txt in txts:
                        fb = fb + txt + '\n'
            
            # old default case, change the order to better fit for https://www.bgq228.com/
            if (len(fb) < 10):    
                # modified in v9.1 to adjust https://www.ibiquges.org/ ; 使用环视
                # contents = re.findall('&nbsp;([^&].*?)\r?<br', full_txt, re.S)
                
                contents = re.findall(r'&nbsp;((?:(?!&nbsp;).)+?)\r?\n?<br', full_txt, re.S)
                for content in contents:
                    fb = fb + content + '\n'
                
            # Added in V8B to adapt to https://www.bqg228.com
            if (len(fb) < 10):
                contents4 = re.findall(r'\s\s([^<]+?)<br /><br />', full_txt, re.S)
                
                for content4 in contents4:
                    fb = fb + content4 + '\n'
                
            # Major modified in v9.4 to adapt to https://www.qqxsnew.com/ and https://www.xiushukong.com/, https://www.qqxsnew.net/, https://www.zxxs123.com/; 
            if(len(fb) < 10):
                contents2 = re.findall(r'\<div id\=\"content\"\>\s+(.+?)\s+\<\/div\>', full_txt, re.S)
                for content2 in contents2:
                    contents3 = re.split('<br><br>',content2)
                    for content3 in contents3:
                        fb = fb + content3 + '\n'
            
            # Added in v9.4 to adapt to https://www.paozww.com/biquge/312161/83543706.html
                        
            if(len(fb) < 10):
                contents7 = re.findall(r'<p>([^<]+?)<\/p>', full_txt, re.S)
                for content7 in contents7:
                    fb = fb + content7 + '\n'
                
        if (len(fb)> 10):
            break
        else:
            retry_count += 1
            time.sleep(1)
            print("Retry " + str(retry_count) + " times for " + url)

    return fb


def download_novel_other(url_index):
    # url0 = 'https://www.xbiquge.la/'

    #url_index = 'https://www.bqg228.com'
    res_index = requests.get(url_index, headers=headers)
    if res_index.status_code == 200:
        try:
            full_txt_index = res_index.content.decode('utf-8')
        except UnicodeDecodeError: 
            full_txt_index = res_index.content.decode('gb18030',errors='ignore')
        
        subs = re.findall('<h1>(.*?)</h1>', full_txt_index, re.S)
        sub = subs[0]

        f = open(sub + '.txt', 'w', encoding='gb18030')
        print("start to download: " + sub)

        index_txt_temp = full_txt_index.replace("\'", "\"")
        try:
            caps = re.findall(
                # changed in the v8B to adapt to https://www.bqg228.com
                r'<dd>\s*?<a [^\r\n]*?href\s?=\"(.*?)</a></dd>', index_txt_temp, re.S)
        except:
            print("Decode Error 1 at " + url_index)
        else:
            for cap in caps:
                index = cap.split('\"')[0]
                title = cap.split('>')[-1]
                f.write('\n' + title + '\n')

                if(index[:4] == 'http'):
                    url_req = index
                else:
                    surhtml = re.search(r'([^/]+\.html)', index).group(1)
                    url_req = url_index + surhtml
                # print(sub + ' - ' + title)
                main_txt = get_info(url_req)
                # 输出之前清理html标签
                main_txt = clean_text(main_txt)
                
                f.write(main_txt + '\n')

                t_wait = random.randint(15, 40)/40.0
                time.sleep(t_wait)

            print("Done: " + sub)
    else:
        pass

def download_novel_yueduba2_cc(url_base):
    # 定义初始URL
    # url_base = "http://www.yueduba2.cc/1565_1565603/"
    # 抓取初始页面
    response = requests.get(url_base)
    soup = BeautifulSoup(response.content, 'html.parser')

    # 找到特定的<meta>标签
    meta_tag = soup.find('meta', property='og:title')
    # 提取content属性值
    sub = meta_tag['content']
    print("Start to download: " + sub)
    # 初始化空字符串
    cached_title = ""
    fb = sub + '\n'  # 添加换行符，使每个页面的内容分开
  
    # 设置计数器
    i = 1

    while True:
        # 构建新的URL
        url0 = f"{url_base}{i}.html"
        
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
        pattern_maintext = r'</div>\s+<p>(.+?)</p><script>'
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
        # print(sub, chapter_title)

        # 更新计数器
        i += 1

        # 随机等待一段时间, 以免被封IP
        # t_wait = random.randint(15, 40)/40.0
        # time.sleep(t_wait)
    fb = clean_text(fb)
    # 将收集到的所有内容覆盖写入到sub为文件名的txt文件中
    with open(sub + '.txt', 'w', encoding='gb18030') as file:
        file.write(fb)
    print("Done: " + sub)

def download_novel(url):
    if 'yueduba2.cc' in url:
        download_novel_yueduba2_cc(url)
    else:
        download_novel_other(url)

if __name__ == '__main__':  
    
    parser = argparse.ArgumentParser()  
    parser.add_argument('-i', '--input_file', type=str, default='download_list10.txt', help='Input file name')  
    parser.add_argument('-t', '--max_workers', type=int, default=8, help='Maximum number of workers')  
    args = parser.parse_args()  
    
    dl_file = args.input_file
    max_workers_limit = args.max_workers  
    try:
        with open(dl_file, 'r') as l_fh:  
            lines0 = l_fh.readlines()  
  
        # 去重复, 以防止线程互锁  
        lines = list(set(lines0))  

        # 创建一个线程池，最大线程数不超过max_workers_limit  
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers_limit) as executor:  
            # 使用线程池并发地执行下载任务  
            future_results = [executor.submit(download_novel, line.rstrip()) for line in lines if len(line.rstrip()) > 3]  
            # 等待所有任务执行完成  
            results = [future.result() for future in concurrent.futures.as_completed(future_results)]
        
        l_fh.close()
  
    except FileNotFoundError:  
        print("文件未找到，请检查文件名和路径。")  
    except Exception as e:  
        print(f"出现错误：{e}")

        
