import time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ProcessPoolExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
import multiprocessing
import threading
import portalocker
from pathlib import Path
import functools
from datetime import datetime

# 导入你的函数
from utils.utils_data import download_history_data
from utils.utils_general import is_trading_day
from stop_loss.stop_loss_main import stop_loss_main as raw_stop_loss_main
from deep_learning.tsmixer import fit_tsmixer_model
from deep_learning.monitor_buy import conditionally_execute_trading
from mini_xtclient.mini_xt import start_miniqmt
from trader.reporter import generate_trading_report
from utils.utils_data import get_max_ask_price, subscribe_real_data
from loggers import logger

# 全局中断事件
stop_event = threading.Event()
stop_loss_process = None

# 定义调度器
jobstores = {
    'default': SQLAlchemyJobStore(url='sqlite:///assets/runtime/jobs.sqlite')
}
executors = {'default': ProcessPoolExecutor(10)}
job_defaults = {
    'coalesce': False,
    'max_instances': 1,
    'misfire_grace_time': 120  # 1小时
}
scheduler = BackgroundScheduler(jobstores=jobstores, executors=executors, job_defaults=job_defaults)

# 作业执行状态追踪
job_status = {}

LOCK_FILE_PATH = Path(__file__).parent.joinpath('assets/runtime/file_lock.lock')


def log_job_execution(event):
    if event.exception:
        logger.error(f"作业 {event.job_id} 执行失败: {event.exception}")
        job_status[event.job_id] = {'status': 'failed', 'last_run': event.scheduled_run_time}
    else:
        logger.info(f"作业 {event.job_id} 执行成功")
        job_status[event.job_id] = {'status': 'success', 'last_run': event.scheduled_run_time}


scheduler.add_listener(log_job_execution, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)


def retry_on_failure(max_attempts=3, delay=10):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    logger.error(f"作业执行失败 (尝试 {attempts}/{max_attempts}): {str(e)}")
                    if attempts < max_attempts:
                        time.sleep(delay)
            logger.critical(f"作业在 {max_attempts} 次尝试后仍然失败")

        return wrapper

    return decorator


def stop_loss_main():
    """为stop_loss_main加锁"""
    logger.info('正在启动stop_loss_main……')
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


@retry_on_failure()
def download_history_data_job():
    if not is_trading_day():
        logger.info(f"今天不是交易日，跳过执行 download_history_data_job。")
        return
    logger.info("开始下载历史数据")
    download_history_data()
    logger.info("历史数据下载完成")


@retry_on_failure()
def fit_tsmixer_model_job():
    if not is_trading_day():
        logger.info(f"今天不是交易日，跳过执行 fit_tsmixer_model_job。")
        return
    logger.info("开始拟合TSMixer模型")
    fit_tsmixer_model()
    logger.info("TSMixer模型拟合完成")


@retry_on_failure()
def conditionally_execute_trading_job():
    if not is_trading_day():
        logger.info(f"今天不是交易日，跳过执行 conditionally_execute_trading_job。")
        return
    logger.info("开始执行交易条件检查")
    conditionally_execute_trading()
    logger.info("交易条件检查完成")


@retry_on_failure()
def generate_trading_report_job():
    if not is_trading_day():
        logger.info(f"今天不是交易日，跳过执行 generate_trading_report_job。")
        return
    logger.info("开始生成交易报告")
    generate_trading_report()
    logger.info("交易报告生成完成")


def add_jobs():
    scheduler.add_job(download_history_data_job, 'cron', day_of_week='mon-fri', hour=9, minute=0, id='download1',
                      replace_existing=True)
    scheduler.add_job(download_history_data_job, 'cron', day_of_week='mon-fri', hour=15, minute=20, id='download2',
                      replace_existing=True)

    scheduler.add_job(fit_tsmixer_model_job, 'cron', day_of_week='mon-fri', hour=9, minute=5, id='fit_model',
                      replace_existing=True)

    scheduler.add_job(conditionally_execute_trading_job, 'cron', day_of_week='mon-fri', hour=14, minute=58,
                      id='trade_condition', replace_existing=True)

    scheduler.add_job(generate_trading_report_job, 'cron', day_of_week='mon-fri', hour=9, minute=20,
                      id='report_0920', replace_existing=True)
    scheduler.add_job(generate_trading_report_job, 'cron', day_of_week='mon-fri', hour=11, minute=35,
                      id='report_1135', replace_existing=True)
    scheduler.add_job(generate_trading_report_job, 'cron', day_of_week='mon-fri', hour=15, minute=5,
                      id='report_1505', replace_existing=True)

    # # 订阅行情数据
    # scheduler.add_job(subscribe_real_data, 'cron', day_of_week='mon-fri', hour=9, minute=29,
    #                   id='subscribe_real_data', replace_existing=True)

    # 控制stop_loss_main的开始与停止
    scheduler.add_job(start_stop_loss, 'cron', day_of_week='mon-fri', hour='9', minute='30-59/10',
                      id='start_stop_loss_morning_9', replace_existing=True)
    scheduler.add_job(start_stop_loss, 'cron', day_of_week='mon-fri', hour='10', minute='0-59/10',
                      id='start_stop_loss_morning_10', replace_existing=True)
    scheduler.add_job(start_stop_loss, 'cron', day_of_week='mon-fri', hour='11', minute='0-29/10',
                      id='start_stop_loss_morning_11', replace_existing=True)
    scheduler.add_job(start_stop_loss, 'cron', day_of_week='mon-fri', hour='13-14', minute='*/10',
                      id='start_stop_loss_afternoon', replace_existing=True)
    scheduler.add_job(stop_stop_loss, 'cron', day_of_week='mon-fri', hour=11, minute=30, id='stop_stop_loss_morning',
                      replace_existing=True)
    scheduler.add_job(stop_stop_loss, 'cron', day_of_week='mon-fri', hour=15, minute=0, id='stop_stop_loss_afternoon',
                      replace_existing=True)

    # 定时监测客户端是否启动
    scheduler.add_job(start_miniqmt, 'cron', day_of_week='mon-fri', minute="*/30", id='start_miniqmt',
                      replace_existing=True, next_run_time=datetime.now())

    # # 测试最大值
    # scheduler.add_job(get_max_ask_price, 'cron', day_of_week='mon-fri', hour='9-14', minute="*/15",
    #                   id='get_max_ask_price', args=('159985.SZ',),
    #                   replace_existing=True, next_run_time=datetime.now())



if __name__ == '__main__':
    try:
        # start_miniqmt()
        logger.info("添加计划")
        add_jobs()
        scheduler.start()

        logger.info("调度器已启动并正在运行...")

        # 主循环
        while True:
            time.sleep(600)
            # 定期检查作业状态
            for job_id, status in job_status.items():
                logger.info(f"作业 {job_id} 状态: {status['status']}, 上次运行: {status['last_run']}")

    except (KeyboardInterrupt, SystemExit):
        logger.info("捕获系统退出信号，准备关闭调度器...")
        scheduler.shutdown()
        logger.info("调度器已成功关闭")
        # 停止其他子进程
        stop_event.set()
        if stop_loss_process and stop_loss_process.is_alive():
            stop_loss_process.join(timeout=5)
            if stop_loss_process.is_alive():
                stop_loss_process.terminate()