import os
import psutil
import subprocess
import time
from pathlib2 import Path

# 配置日志记录器
from loggers import logger
from config import config
from .pyauto import WindowRegexFinder


class ProgramMonitor:
    MINIXT_PROCESS_NAME = "XtMiniQmt.exe"
    LOGIN_PROCESS_NAME = "XtItClient.exe"

    def __init__(self):
        # 加载配置文件
        self.program_name = config['xt_client'].get('program_dir')
        if not self.program_name:
            raise KeyError('在"xt_client"节中未找到键"program_dir"。')

        self.check_interval = config.getint('xt_client', 'check_interval', fallback=60)

    def is_program_running(self):
        """检查是否有指定名称的程序正在运行"""
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] == self.MINIXT_PROCESS_NAME:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return False

    def is_login_progress_running(self):
        """检查是否有指定名称的登录进程正在运行"""
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] == self.LOGIN_PROCESS_NAME:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return False

    def start_program(self):
        """启动指定路径的程序"""
        if self.is_program_running():
            logger.info("迅投程序已运行，无需启动。")
        try:
            subprocess.Popen(self.program_name)
            logger.info(f"程序 {self.program_name} 已启动。")
        except Exception as e:
            logger.error(f"无法启动程序 {self.program_name}：{e}")
        # 点击登录
        time.sleep(15)
        if self.is_login_progress_running():
            finder = WindowRegexFinder(r"e海方舟-量化交易版[.\d ]+")
            # 查找窗口句柄
            finder.find_window()
            # 将窗口置顶
            finder.bring_window_to_top()
            # 查找并点击图像按钮
            path = Path(__file__).parent.parent / "config/login_button.PNG"
            finder.find_and_click_image_button(str(path))

    def stop_program(self):
        """停止指定名称的程序"""
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] == self.MINIXT_PROCESS_NAME:
                    proc.terminate()
                    logger.info(f"程序 {self.MINIXT_PROCESS_NAME} 已停止。")
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
                logger.error(f"无法停止程序 {self.MINIXT_PROCESS_NAME}：{e}")
            try:
                if proc.info['name'] == self.LOGIN_PROCESS_NAME:
                    proc.terminate()
                    logger.info(f"程序 {self.LOGIN_PROCESS_NAME} 已停止。")
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
                logger.error(f"无法停止程序 {self.LOGIN_PROCESS_NAME}：{e}")

    def restart_program(self):
        """重启指定名称的程序"""
        logger.info("正在重启程序...")
        self.stop_program()
        time.sleep(5)  # 等待进程完全结束
        self.start_program()

    def monitor(self):
        """开始监控程序状态"""
        while True:
            if not self.is_program_running():
                logger.info(f"检测到 {self.MINIXT_PROCESS_NAME} 未启动，正在启动...")
                self.start_program()
            else:
                logger.info(f"{self.MINIXT_PROCESS_NAME} 正在运行。")

            # 每隔指定时间间隔检测一次
            time.sleep(self.check_interval)


if __name__ == "__main__":
    monitor = ProgramMonitor()
    monitor.monitor()