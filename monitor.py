from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ProcessPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
import portalocker
import threading
import time
import multiprocessing
from pathlib import Path

# 导入您的函数
from utils.utils_data import download_history_data
from utils.utils_general import is_trading_day
from stop_loss.stop_loss_main import stop_loss_main as raw_stop_loss_main
from deep_learning.tsmixer import fit_tsmixer_model
from deep_learning.monitor_buy import conditionally_execute_trading
from mini_xtclient.mini_xt import start_miniqmt
from trader.reporter import generate_trading_report
from loggers import logger

# 全局中断事件
stop_event = threading.Event()
stop_loss_process = None

# 定义调度器
jobstores = {'default': MemoryJobStore()}
executors = {'default': ProcessPoolExecutor(10)}
job_defaults = {
    'coalesce': True,
    'max_instances': 1,
    'misfire_grace_time': 60  # 增加到60秒
}
scheduler = BackgroundScheduler(jobstores=jobstores, executors=executors, job_defaults=job_defaults)
scheduler.start()

LOCK_FILE_PATH = Path(__file__).parent.joinpath('assets/runtime/file_lock.lock')


def stop_loss_main():
    """为stop_loss_main加锁"""
    logger.info('正在启动stop_loss_main……')
    # 使用更简洁的 with open 语句
    with LOCK_FILE_PATH.open('w') as lock_file:
        try:
            portalocker.lock(lock_file, portalocker.LOCK_EX | portalocker.LOCK_NB)
            try:
                raw_stop_loss_main()
            except Exception as e:
                logger.error(f"stop_loss_main 发生错误: {e}")
            finally:
                portalocker.unlock(lock_file)
        except portalocker.exceptions.LockException:
            logger.info("stop_loss_main 已在运行，忽略此次调用。")


def is_trading_day_decorator(func):
    def wrapper(*args, **kwargs):
        if not is_trading_day():
            logger.info(f"今天不是交易日，跳过执行{func.__name__}。")
            return
        return func(*args, **kwargs)
    return wrapper



def start_stop_loss():
    """启动stop_loss_main"""
    logger.info('正在启动stop_loss_main……')
    global stop_loss_process
    if not is_trading_day():
        logger.info("今天不是交易日，无需启动start_stop_loss")
        return False
    if stop_loss_process is None or not stop_loss_process.is_alive():
        stop_event.clear()  # 确保事件被清除
        stop_loss_process = multiprocessing.Process(target=stop_loss_main)
        stop_loss_process.start()
        logger.info("stop_loss_main 已启动")
    else:
        logger.info("stop_loss_main 进程已存在，无需重复启动")


def stop_stop_loss():
    logger.info("正在停止stop_loss_main")
    global stop_loss_process
    if stop_loss_process is not None and stop_loss_process.is_alive():
        logger.info("正在停止stop_loss_main")
        stop_event.set()
        stop_loss_process.join(timeout=10)  # 等待进程结束，最多等待10秒
        if stop_loss_process.is_alive():
            stop_loss_process.terminate()  # 如果进程仍然活跃，强制终止
        stop_loss_process = None
        logger.info("已停止stop_loss_main")
    else:
        logger.info('stop_loss_main进程未运行，无需停止操作。')


def add_jobs():
    @is_trading_day_decorator
    def download_history_data_job():
        download_history_data()

    @is_trading_day_decorator
    def fit_tsmixer_model_job():
        fit_tsmixer_model()

    @is_trading_day_decorator
    def conditionally_execute_trading_job():
        conditionally_execute_trading()

    @is_trading_day_decorator
    def generate_trading_report_job():
        generate_trading_report()

    # 每个工作日特定时间调用
    scheduler.add_job(download_history_data_job, 'cron', day_of_week='mon-fri', hour=9, minute=0, id='download1',
                      replace_existing=True)
    scheduler.add_job(download_history_data_job, 'cron', day_of_week='mon-fri', hour=15, minute=20, id='download2',
                      replace_existing=True)
    scheduler.add_job(fit_tsmixer_model_job, 'cron', day_of_week='mon-fri', hour=9, minute=5, id='fit_model',
                      replace_existing=True)
    scheduler.add_job(conditionally_execute_trading_job, 'cron', day_of_week='mon-fri', hour=14, minute=58,
                      id='trade_condition', replace_existing=True)
    scheduler.add_job(generate_trading_report_job, 'cron', day_of_week='mon-fri', hour='9,11,15', minute='20,35,5',
                      id='report', replace_existing=True)

    # 控制stop_loss_main的开始与停止
    scheduler.add_job(start_stop_loss, 'cron', day_of_week='mon-fri', hour='9', minute='29-59/10',
                      id='start_stop_loss_morning_9', replace_existing=True)
    scheduler.add_job(start_stop_loss, 'cron', day_of_week='mon-fri', hour='10-11', minute='0-29/10',
                      id='start_stop_loss_morning', replace_existing=True)
    scheduler.add_job(start_stop_loss, 'cron', day_of_week='mon-fri', hour='13-14', minute='*/10',
                      id='start_stop_loss_afternoon', replace_existing=True)
    scheduler.add_job(stop_stop_loss, 'cron', day_of_week='mon-fri', hour=11, minute=30, id='stop_stop_loss_morning',
                      replace_existing=True)
    scheduler.add_job(stop_stop_loss, 'cron', day_of_week='mon-fri', hour=15, minute=0, id='stop_stop_loss_afternoon',
                      replace_existing=True)


if __name__ == '__main__':
    try:
        start_miniqmt()
        download_history_data()
        fit_tsmixer_model()
        generate_trading_report()
        stop_loss_main()

        # 添加任务
        add_jobs()

        while True:
            time.sleep(600)

    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        stop_event.set()
        if stop_loss_process and stop_loss_process.is_alive():
            stop_loss_process.join(timeout=5)
            if stop_loss_process.is_alive():
                stop_loss_process.terminate()