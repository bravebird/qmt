import time
import random
from datetime import datetime, timedelta
from xtquant import xtdata

def generate_session_id():
    """
    生成一个基于日期和时间戳的唯一 32 位整数会话 ID，确保在同一天内不重复
    :return: 唯一的会话 ID 整数
    """
    # 获取当前日期和时间的秒级时间戳
    now = time.localtime()
    date_str = time.strftime("%Y%m%d", now)  # 格式化为 YYYYMMDD
    timestamp = int(time.mktime(now))  # 当前时间的秒级时间戳

    # 生成一个 12 位的随机数
    random_number = random.randint(0, 4095)  # 12 位的随机数范围是 0 到 4095

    # 将日期字符串转换为整数
    date_int = int(date_str)

    # 将日期整数和时间戳的最后 20 位组合成一个 32 位整数
    session_id = (date_int << 12) | random_number

    return session_id


def is_trading_day():
    """
    判断当天是否为交易日。利用xtquant的get_trading_calendar方法获得交易信息。
    """
    today = datetime.now().strftime("%Y%m%d")
    future_date = (datetime.now() + timedelta(days=1)).strftime("%Y%m%d")
    calendar = xtdata.get_trading_calendar("SH", start_time=today, end_time=future_date)
    return any(today == str(date) for date in calendar)

def is_transaction_hour():
    """
    判断当前时间是否为交易时间
    :return:
    """
    today = datetime.now()
    morning_start = today.replace(hour=9, minute=30, second=0, microsecond=0)
    morning_end = today.replace(hour=11, minute=30, second=0, microsecond=0)
    afternoon_start = today.replace(hour=13, minute=0, second=0, microsecond=0)
    afternoon_end = today.replace(hour=15, minute=0, second=0, microsecond=0)
    return (morning_start <= today <= morning_end) \
        or (afternoon_start <= today <= afternoon_end)