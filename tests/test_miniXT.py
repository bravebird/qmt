import os
import configparser
import pytest


def test_start_mini_xt():
    from mini_xtclient.mini_xt import ProgramMonitor

    # 获取项目根目录路径  
    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    # 使用项目根目录构建config文件路径  
    config_path = os.path.join(project_dir, 'config', 'config.ini')

    monitor = ProgramMonitor(config_path)
    monitor.monitor()


# def test_click_btn():
#     from mini_xtclient.pyauto import WinController
#     wc = WinController(window_title=)