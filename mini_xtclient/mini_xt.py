import os
import configparser
import psutil
import subprocess
import time


class ProgramMonitor:
    def __init__(self, config_path):
        # 打印用于调试的配置信息
        print(f"Loading configuration from: {config_path}")

        config = configparser.ConfigParser()
        files_read = config.read(config_path)

        if not files_read:
            raise FileNotFoundError(f"Config file not found: {config_path}")

        if 'xt_client' not in config:
            raise KeyError('The section xt_client is missing in the configuration file.')

        self.program_name = config['xt_client']['program_dir']
        self.process_name = config['xt_client']['process_name']
        self.check_interval = config.getint('xt_client', 'check_interval')

    def is_program_running(self):
        """检查是否有指定名称的程序正在运行"""
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] == self.process_name:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return False

    def start_program(self):
        """启动指定路径的程序"""
        try:
            subprocess.Popen(self.program_name)
            print(f"程序 {self.program_name} 已启动。")
        except Exception as e:
            print(f"无法启动程序 {self.program_name}：{e}")

    def monitor(self):
        """开始监控程序状态"""
        while True:
            if not self.is_program_running():
                print(f"检测到 {self.process_name} 未启动，正在启动...")
                self.start_program()
            else:
                print(f"{self.process_name} 正在运行。")

                # 每隔指定时间间隔检测一次
            time.sleep(self.check_interval)


if __name__ == "__main__":
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'config.ini')
    monitor = ProgramMonitor(config_path)
    monitor.monitor()