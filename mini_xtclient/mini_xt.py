import os
import psutil
import subprocess
import time
from pathlib import Path
from loggers import logger
from config import config
from mini_xtclient.pyauto import WindowRegexFinder
from multiprocessing import Lock, Queue, Process


class ProgramMonitor:
    MINIXT_PROCESS_NAME = "XtMiniQmt.exe"
    LOGIN_PROCESS_NAME = "XtItClient.exe"
    _instance = None
    lock = Lock()
    task_queue = Queue()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
        self._initialized = True

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

    def start_program(self, auto_login=True):
        """启动指定路径的程序，确保操作在同一时刻只被一个进程执行"""
        with self.lock:
            if self.is_program_running():
                logger.info("迅投程序已运行，无需启动。")
                return
            try:
                subprocess.Popen(self.program_name)
                logger.info(f"程序 {self.program_name} 已启动。")
            except Exception as e:
                logger.error(f"无法启动程序 {self.program_name}：{e}")
                return

                # 点击登录
            time.sleep(20)
            if self.is_login_progress_running():
                finder = WindowRegexFinder(r"e海方舟-量化交易版[.\d ]+")
                # 查找窗口句柄
                finder.find_window()
                # 将窗口置顶
                finder.bring_window_to_top()
                # 查找并点击图像按钮
                if not auto_login:
                    path = Path(__file__).parent.parent / "config/xt_login_button.PNG"
                    finder.find_and_click_image_button(str(path))

    def stop_program(self):
        """停止指定名称的程序，确保操作在同一时刻只被一个进程执行"""
        with self.lock:
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
        """重启指定名称的程序，确保操作在同一时刻只被一个进程执行"""
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

    @classmethod
    def add_task(cls, task, *args, **kwargs):
        """将任务添加到队列"""
        cls.task_queue.put((task, args, kwargs))

    @classmethod
    def worker(cls):
        """从队列中获取任务并执行，确保任务的顺序执行"""
        while True:
            task, args, kwargs = cls.task_queue.get()
            logger.info(f"执行任务: {task.__name__}")
            task(*args, **kwargs)
            cls.task_queue.task_done()

def start_miniqmt():
    monitor = ProgramMonitor()
    monitor.start_program()

if __name__ == "__main__":
    monitor = ProgramMonitor()
    monitor.start_program()

    # 创建一个额外的进程以监控队列中的任务执行
    worker_process = Process(target=ProgramMonitor.worker)
    worker_process.daemon = True  # 设置为守护进程
    worker_process.start()

    # 添加任务来模拟多进程环境中的任务调用
    ProgramMonitor.add_task(monitor.monitor)
    ProgramMonitor.add_task(monitor.start_program)
    ProgramMonitor.add_task(monitor.stop_program)
    ProgramMonitor.add_task(monitor.restart_program)

    worker_process.join()  # 等待工作进程执行完队列中的所有任务