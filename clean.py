import os  
import shutil  
  
# 获取当前工作目录  
current_dir = os.getcwd()  
  
# 设定目标文件夹路径  
novels_dir = os.path.join(current_dir, 'novels')  
  
# 如果目标文件夹不存在，创建它  
if not os.path.exists(novels_dir):  
    os.makedirs(novels_dir)  
  
# 遍历当前目录下的所有文件  
for file in os.listdir(current_dir):  
    # 如果文件是txt文件，并且文件名中不包含"download_list"  
    if file.endswith('.txt') and 'download_list' not in file:  
        # 获取文件的完整路径  
        file_path = os.path.join(current_dir, file)  
        # 设定文件在目标文件夹的路径  
        novels_path = os.path.join(novels_dir, file)  
        # 移动文件到目标文件夹  
        shutil.move(file_path, novels_path)

