from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ProcessPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from datetime import datetime
import time

# 自定义的调度对象
from utils.utils_data import download_history_data
from utils.utils_general import is_trading_day
from stop_loss.stop_loss_main import stop_loss_main
from deep_learning.tsmixer import fit_tsmixer_model
from deep_learning.monitor_buy import conditionally_execute_trading
from mini_xtclient.mini_xt import start_miniqmt
from trader.reporter import generate_trading_report
from loggers import logger

# pre_00: 调度器设置
# 配置调度器的 jobstore 和 executor
jobstores = {
    'default': MemoryJobStore()
}

executors = {
    'default': ProcessPoolExecutor(max_workers=4)
}

job_defaults = {
    'misfire_grace_time': 300,  # 5分钟的宽限时间
    'coalesce': False,
    'max_instances': 1
}

scheduler = BackgroundScheduler(jobstores=jobstores, executors=executors, job_defaults=job_defaults)


# 添加作业函数
def add_jobs():
    now = datetime.now()
    if not is_trading_day():
        logger.info("今天不是交易日，程序放假。")
        return False
    # 避免重复添加作业
    if scheduler.get_job('download_history_data'):
        logger.info("作业已经存在，不重复添加作业。")
        return True

    # 启动
    scheduler.add_job(
        start_miniqmt,
        'cron',
        day_of_week='mon-fri',  # 每个工作日运行
        hour='9-17',
        minute=0,
        second=0,
        id='start_miniqmt',
        next_run_time=now
    )

    # 定时下载数据
    scheduler.add_job(
        download_history_data,
        'cron',
        day_of_week='mon-fri',  # 每个工作日运行
        hour='9,13,15',
        minute=10,
        second=0,
        id='download_history_data'
    )

    # 止损
    scheduler.add_job(
        stop_loss_main,
        'cron',
        day_of_week='mon-fri',  # 每个工作日运行
        hour='9-14',
        minute=20,
        id='stop_loss_main',
        next_run_time=now
    )

    # 训练模型
    scheduler.add_job(
        fit_tsmixer_model,
        'cron',
        day_of_week='mon-fri',  # 每个工作日运行
        hour=9,
        minute=10,
        second=0,
        id='fit_tsmixer_model'
    )

    # 盯盘交易
    scheduler.add_job(
        conditionally_execute_trading,
        'cron',
        day_of_week='mon-fri',  # 每个工作日运行
        hour='14',
        minute='58',  # 每个小时的20和50分钟运行
        second=0,
        id='conditionally_execute_trading'
    )

    # 交易报告
    scheduler.add_job(
        generate_trading_report,
        'cron',
        day_of_week='mon-fri',  # 每个工作日运行
        hour='15',
        minute='15',
        second=0,
        id='generate_trading_report',
        next_run_time=now
    )


def remove_jobs():
    scheduler.remove_all_jobs()
    logger.info("所有作业已移除。")


# 每天18:00结束所有作业
# scheduler.add_job(
#     remove_jobs,
#     'cron',
#     hour=16,
#     minute=0,
#     second=0,
#     id='remove_all_jobs'
# )

# 每天08:00重新添加作业
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
        scheduler.shutdown()
