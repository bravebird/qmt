import xtquant.xtdata as xtdata
from datetime import datetime
import pandas as pd
from pathlib2 import Path
from utils.utils_data import get_targets_list_from_csv  # 获取股票列表
from loggers import logger


def download_stock_data(period='1d', start_time=None, end_time=None, callback=None):
    """
    从 CSV 文件获取股票列表并下载历史数据。

    :param period: 时间周期，默认 '1d'
    :param start_time: 起始时间，格式为 'YYYYMMDD'，默认 '20200101'
    :param end_time: 结束时间，格式为 'YYYYMMDD'，默认当前日期
    :param callback: 下载数据时的回调函数，默认 None
    """
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
        xtdata.download_history_data(stock, period, start_time, end_time, incrementally=True)


def get_stock_data_as_dataframe(period='1d', start_time=None, end_time=None):
    """
    获取股票历史数据并返回 pandas DataFrame。

    :param stock_list: 要获取数据的股票列表
    :param period: 时间周期，默认 '1d'
    :param start_time: 起始时间，格式为 'YYYYMMDD'
    :param end_time: 结束时间，格式为 'YYYYMMDD'，默认当前日期
    :return: 包含股票数据的 pandas DataFrame
    """
    if start_time is None:
        start_time = '20200101'
    if end_time is None:
        end_time = datetime.now().strftime('%Y%m%d%H%M%S')
    stock_list = get_targets_list_from_csv()

    # 获取所有股票的历史数据
    market_data = xtdata.get_market_data_ex(
        field_list=[],  # 为空时，获取全部字段
        stock_list=stock_list,
        period=period,
        start_time=start_time,
        end_time=end_time,
        count=-1,
        dividend_type='front_ratio',
        fill_data=True
    )

    # 数据整合到一个 pd.DataFrame 中， 数据结构优化
    df_list = []
    for field, df in market_data.items():
        df['stock_code'] = field
        df.index.name = 'date'
        df_list.append(df)
    combined_df = pd.concat(df_list, axis=0)

    return combined_df


path = Path(__file__).parent.parent


def save_data_to_csv(df, filename=(path / 'assets/data/combined_market_data.csv').absolute()):
    """
    将数据保存到CSV文件中。

    :param df: 数据 DataFrame
    :param filename: 文件名，默认为 'combined_market_data.csv'
    """
    logger.info(filename)
    df.to_csv(filename)
    print(f'Saved data to {filename}')


def download_get_and_save_kline_date(period='1d', start_time=None, end_time=None, callback=None):
    # 下载数据
    download_stock_data(period=period, start_time=start_time, end_time=end_time, callback=callback)
    # 获取股票数据并存储到 DataFrame
    combined_df = get_stock_data_as_dataframe(period=period, start_time=start_time, end_time=end_time)

    # 打印前几行数据并保存到 CSV 文件
    print("Combined data:")
    print(combined_df.tail())

    # 将数据保存为 CSV 文件
    now = datetime.now().strftime('%Y%m%d%H%M%S')
    filename = Path(__file__).parent.parent / f'assets/data/combined_{period}_data_{now}.csv'
    save_data_to_csv(combined_df, filename=filename)
    return combined_df


if __name__ == '__main__':
    import schedule, time

    # 获取今天的日期
    today = datetime.now().date()

    # 设置定时任务
    schedule.every().day.at("10:00").do(download_get_and_save_kline_date)
    schedule.every().day.at("11:00").do(download_get_and_save_kline_date)
    schedule.every().day.at("11:29").do(download_get_and_save_kline_date)

    # 启动时运行一次
    download_get_and_save_kline_date()

    while True:
        # 检查今天的日期
        if datetime.now().date() != today:
            break  # 如果不是今天，退出循环

        schedule.run_pending()
        time.sleep(1)
