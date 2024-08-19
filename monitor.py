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

# 创建全局的中断事件和重设事件
stop_event = threading.Event()
add_jobs_event = threading.Event()

# pre_00: 调度器设置
jobstores = {
    'default': MemoryJobStore()
}

executors = {
    'default': ProcessPoolExecutor(max_workers=4)
}

job_defaults = {
    'misfire_grace_time': 300,  # 5分钟的宽限时间
    'coalesce': False,
    'max_instances': 50
}

scheduler = BackgroundScheduler(jobstores=jobstores, executors=executors, job_defaults=job_defaults)

# 示例任务（用中断信号控制）
def monitored_task(task_func, *args, **kwargs):
    logger.info(f"Starting task {task_func.__name__}")
    try:
        if not stop_event.is_set() and not add_jobs_event.is_set():
            task_func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Error in task {task_func.__name__}: {e}")
    logger.info(f"Stopping task {task_func.__name__}")

# 添加作业函数
def add_jobs():
    now = datetime.now()
    if not is_trading_day():
        logger.info("今天不是交易日，程序放假。")
        return False

    # 核心改动: 针对个别任务进行监控，确保在任务不存在或错误后重新添加
    job_ids = [
        ('start_miniqmt', start_miniqmt, '9-14', 0),
        ('download_history_data', download_history_data, '9,12,15', 10),
        ('stop_loss_main', stop_loss_main, '9-14', 20),
        ('fit_tsmixer_model', fit_tsmixer_model, 9, 10),
        ('conditionally_execute_trading', conditionally_execute_trading, 14, 58),
        ('generate_trading_report', generate_trading_report, "9,12,15", 5)
    ]

    for job_id, task, hour, minute in job_ids:
        existing_job = scheduler.get_job(job_id)
        if not existing_job or existing_job._instance_limit == 0:
            logger.info(f"添加任务：{job_id}.")
            scheduler.add_job(
                monitored_task,
                'cron',
                args=(task,),
                day_of_week='mon-fri',
                hour=hour,
                minute=minute,
                second=0,
                id=job_id,
                next_run_time=now
            )

def remove_jobs_and_stop_tasks():
    logger.info("移除所有job")
    stop_event.set()  # 通知所有任务停止
    scheduler.remove_all_jobs()
    logger.info("所有作业已移除，正在停止任务。")
    add_jobs_event.clear()  # 重置添加作业的事件

# 每天08:59重新添加作业
def initialize_new_day_jobs():
    if not add_jobs_event.is_set():
        logger.info("重新初始化新一天的任务")
        add_jobs_event.set()
        add_jobs()  # 确保被调用以添加新任务

scheduler.add_job(
    initialize_new_day_jobs,
    'cron',
    hour=8,
    minute=0,
    second=0,
    id='initialize_new_day_jobs'
)

# 每天16:00结束所有作业
scheduler.add_job(
    remove_jobs_and_stop_tasks,
    'cron',
    hour=16,
    minute=0,
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