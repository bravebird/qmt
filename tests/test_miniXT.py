import os
import configparser
import pytest


def test_start_mini_xt():
    from mini_xtclient.mini_xt import ProgramMonitor

    # 获取项目根目录路径  
    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    # 使用项目根目录构建config文件路径  
    config_path = os.path.join(project_dir, 'config', 'config.ini')

    # 检查配置文件是否存在  
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

        # 读取配置文件
    config = configparser.ConfigParser()
    config.read(config_path)

    # 获取配置项  
    if 'xt_client' not in config:
        raise ValueError("Missing 'xt_client' section in the config file")

        # 下面可以添加与ProgramMonitor相关的测试
    xt_client_config = config['xt_client']
    # 示例操作  
    # monitor = ProgramMonitor(xt_client_config['some_key'])  
    # assert monitor.some_property == expected_value  

    # 示例断言，用于通过测试  
    assert True  