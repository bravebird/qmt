import os
from pathlib2 import Path
import matplotlib.pyplot as plt

# 设置工作目录
work_path = Path(__file__).parent.parent
os.chdir(work_path)
print(f"当前工作目录：{os.getcwd()}")

# 设置支持中文的字体
plt.rcParams['font.sans-serif'] = ['SimHei']   # 使用黑体
plt.rcParams['axes.unicode_minus'] = False     # 解决负号显示问题
print(f"matplotlib显示字体已设置为中文。")