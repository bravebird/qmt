import csv
from xtquant import xtdata
from datetime import datetime
from pathlib import Path
# 自定义
from config import config
from loggers import logger
from utils.utils_general import is_trading_day


def get_targets_list_from_csv():
    """
    从csv文件中读取股票代码列表
    """
    csv_file_path = str((Path(__file__).parent.parent / config['data']['investment_targets']).absolute())
    stock_list = []
    try:
        with open(csv_file_path, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['STATUS'] == 'True':
                    stock_list.append(row['SECURE'])
    except Exception as e:
        logger.error(f"Error reading CSV file: {e}")
    return stock_list



def get_max_ask_price(stock_code):
    """
    获取指定股票代码的五档行情最高报价

    :param stock_code: 股票代码，例如 "000001.SZ"
    :return: 最新股价，如果获取失败则返回 None
    """
    try:
        # 确保 MiniQmt 已经有所需的数据
        code_list = [stock_code]
        data = xtdata.get_full_tick(code_list)

        if stock_code in data and bool(data[stock_code]):
            time = data[stock_code]['timetag']
            max_ask_price = max(data[stock_code]['askPrice'] + data[stock_code]['bidPrice'])

            logger.info(f"股票:{stock_code}; 时间:{time}; 价格:{max_ask_price}")
            return max_ask_price
        else:
            logger.error(f"未能获取股票 {stock_code} 的数据")
            return None
    except Exception as e:
        logger.error(f"获取股票 {stock_code} 的数据时发生错误: {e}")
        return None


def on_subscribe_data(datas):
    for stock_code in datas:
        print(stock_code, datas[stock_code])

def subscribe_real_data():
    if not is_trading_day():
        logger.info("今天不是交易日")
        return False
    res = xtdata.connect()
    stock_list = get_targets_list_from_csv()
    xtdata.subscribe_whole_quote(stock_list)
    logger.info(f"订阅全推行情:{res}")
    xtdata.run()


def download_history_data(period='1d', start_time=None, end_time=None,):
    """
    从 CSV 文件获取股票列表并下载历史数据。

    :param period: 时间周期，默认 '1d'
    :param start_time: 起始时间，格式为 'YYYYMMDD'，默认 '20200101'
    :param end_time: 结束时间，格式为 'YYYYMMDD'，默认当前日期
    :param callback: 下载数据时的回调函数，默认 None
    """
    if not is_trading_day():
        logger.info("今天不是交易日")
        return False
    # 获取股票列表
    stock_list = get_targets_list_from_csv()

    # 如果未提供 start_time，则默认设置为 '20200101'
    if start_time is None:
        start_time = '20200101'

    # 如果未提供 end_time，则设置为当前日期，格式为 'YYYYMMDD'
    if end_time is None:
        end_time = datetime.now().strftime('%Y%m%d%H%M%S')

    # 调用 xtdata.download_history_data2 方法下载历史数据
    for stock in stock_list:
        xtdata.download_history_data(stock, period, start_time, end_time)
    logger.info("数据下载完成。")


if __name__ == '__main__':
    subscribe_real_data()
    # get_max_ask_price("000001.SZ")

