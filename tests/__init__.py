import os
from pathlib2 import Path

# 修改工作目录
wd = Path(__file__).parent.parent
os.chdir(wd)