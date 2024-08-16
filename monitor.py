from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ProcessPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from datetime import datetime
import threading
import time

# 自定义的调度对象（任务函数）
from utils.utils_data import download_history_data
from utils.utils_general import is_trading_day
from stop_loss.stop_loss_main import stop_loss_main
from deep_learning.tsmixer import fit_tsmixer_model
from deep_learning.monitor_buy import conditionally_execute_trading
from mini_xtclient.mini_xt import start_miniqmt
from trader.reporter import generate_trading_report
# from utils.utils_data import subscribe_real_data
from loggers import logger

# 创建一个全局的中断事件
stop_event = threading.Event()

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
        while not stop_event.is_set():
            task_func(*args, **kwargs)
            break
    except Exception as e:
        logger.error(f"Error in task {task_func.__name__}: {e}")
        # 这里可以选择重新添加任务，或记录更详细的错误日志
    logger.info(f"Stopping task {task_func.__name__}")

# 添加作业函数
def add_jobs():
    now = datetime.now()
    if not is_trading_day():
        logger.info("今天不是交易日，程序放假。")
        return False

    # 核心改动: 针对个别任务进行监控，确保在任务不存在或错误后重新添加
    job_ids = [
        ('start_miniqmt', start_miniqmt, '9-17', 0),
        ('download_history_data', download_history_data, '9,12,15', 10),
        ('stop_loss_main', stop_loss_main, '9-14', 20),
        ('fit_tsmixer_model', fit_tsmixer_model, 9, 10),
        ('conditionally_execute_trading', conditionally_execute_trading, 14, 58),
        ('generate_trading_report', generate_trading_report, 15, 5)
    ]

    for job_id, task, hour, minute in job_ids:
        existing_job = scheduler.get_job(job_id)
        # 作业不存在或曾运行错误，可以考虑通过某种标志或状态检查来决定
        if not existing_job or existing_job._instance_limit == 0:  # 简化示例，具体逻辑可根据实际情况调整
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
    stop_event.set()  # 触发停止事件，通知所有任务停止
    scheduler.remove_all_jobs()
    logger.info("所有作业已移除，正在停止任务。")

# 每天16:00结束所有作业
scheduler.add_job(
    remove_jobs_and_stop_tasks,
    'cron',
    hour=16,
    minute=0,
    second=0,
    id='remove_all_jobs'
)

# 每天08:59重新添加作业
scheduler.add_job(
    add_jobs,
    'cron',
    hour=8,
    minute=59,
    second=0,
    id='add_jobs'
)

if __name__ == '__main__':
    # 启动调度器并添加初始作业
    scheduler.start()
    logger.info("添加job.")
    add_jobs()  # 启动时运行一次

    try:
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down scheduler.")
        stop_event.set()
        scheduler.shutdown()