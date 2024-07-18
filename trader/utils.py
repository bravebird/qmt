import time
import random

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