import configparser
from pathlib2 import Path

config_path = Path(__file__).parent.parent / "config/config.ini"
# 加载配置文件
config = configparser.ConfigParser()
files_read = config.read(config_path.as_posix())
if not files_read:
    raise FileNotFoundError(f"配置文件未找到: {config_path}")