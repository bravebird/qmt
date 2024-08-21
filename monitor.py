from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ProcessPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from datetime import datetime
import threading
import time
from utils.utils_data import download_history_data
from utils.utils_general import is_trading_day
from stop_loss.stop_loss_main import stop_loss_main
from deep_learning.tsmixer import fit_tsmixer_model
from deep_learning.monitor_buy import conditionally_execute_trading
from mini_xtclient.mini_xt import start_miniqmt
from trader.reporter import generate_trading_report
from loggers import logger

# 全局中断事件
stop_event = threading.Event()
job_lock = threading.Lock()  # 用于同步任务执行

# 调度器设置
jobstores = {
    'default': MemoryJobStore()
}

executors = {
    'default': ProcessPoolExecutor(max_workers=4)
}

job_defaults = {
    'misfire_grace_time': 300,
    'coalesce': False,
    'max_instances': 1  # 确保每个作业在任意时间只有一个实例运行
}

scheduler = BackgroundScheduler(jobstores=jobstores, executors=executors, job_defaults=job_defaults)

# 监控任务函数
def monitored_task(task_func, *args, **kwargs):
    logger.info(f"Starting task {task_func.__name__}")
    with job_lock:  # 防止多个线程同时进入
        try:
            if not stop_event.is_set():
                task_func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in task {task_func.__name__}: {e}")
    logger.info(f"Finished task {task_func.__name__}")

# 添加作业函数
def add_jobs():
    if not is_trading_day():
        logger.info("今天不是交易日，程序放假。")
        return

    job_ids = [
        ('start_miniqmt', start_miniqmt, '9-14', 0),
        ('download_history_data', download_history_data, '9,12,15', 10),
        ('fit_tsmixer_model', fit_tsmixer_model, 9, 10),
        ('conditionally_execute_trading', conditionally_execute_trading, 14, 58),
        ('generate_trading_report', generate_trading_report, "9,12,15", 5)
    ]

    for job_id, task, hour, minute in job_ids:
        existing_job = scheduler.get_job(job_id)
        if not existing_job:
            logger.info(f"Adding job: {job_id}.")
            scheduler.add_job(
                monitored_task,
                'cron',
                args=(task,),
                day_of_week='mon-fri',
                hour=hour,
                minute=minute,
                second=0,
                id=job_id
            )

# 单独线程处理可能阻塞的任务
def run_stop_loss_main():
    logger.info("Running stop_loss_main in a separate thread.")
    while not stop_event.is_set():
        with job_lock:
            try:
                stop_loss_main()
            except Exception as e:
                logger.error(f"Error in stop_loss_main: {e}")
            time.sleep(10)

def remove_jobs_and_stop_tasks():
    logger.info("移除所有job")
    stop_event.set()
    scheduler.remove_all_jobs()
    logger.info("所有作业已移除，正在停止任务。")

# 每天初始化新作业
def initialize_new_day_jobs():
    logger.info("重新初始化新一天的任务")
    add_jobs()
    stop_event.clear()
    stop_loss_thread = threading.Thread(target=run_stop_loss_main)
    stop_loss_thread.start()

# 初始化调度器，每天在指定时间添加新作业
scheduler.add_job(
    initialize_new_day_jobs,
    'cron',
    hour="8,12",
    minute=0,
    second=0,
    id='initialize_new_day_jobs'
)

# 在特定时间移除所有作业以结束
scheduler.add_job(
    remove_jobs_and_stop_tasks,
    'cron',
    hour="11,15",
    minute=59,
    second=0,
    id='remove_all_jobs'
)

if __name__ == '__main__':
    scheduler.start()
    logger.info("启动并初始化作业")
    initialize_new_day_jobs()  # 启动时运行一次

    try:
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        logger.info("即将关闭调度器")
        stop_event.set()
        scheduler.shutdown()