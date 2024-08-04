import os
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
    stock_list = get_targets_list_from_csv()

    if start_time is None:
        start_time = '20200101'
    if end_time is None:
        end_time = datetime.now().strftime('%Y%m%d%H%M%S')

    for stock in stock_list:
        try:
            xtdata.download_history_data(stock, period, start_time, end_time, incrementally=True)
            logger.info(f"成功下载股票数据：{stock}")
        except Exception as e:
            logger.error(f"下载股票数据失败：{stock}，错误信息：{e}")


def get_stock_data_as_dataframe(period='1d', start_time=None, end_time=None):
    """
    获取股票历史数据并返回 pandas DataFrame。

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

    try:
        market_data = xtdata.get_market_data_ex(
            field_list=[],
            stock_list=stock_list,
            period=period,
            start_time=start_time,
            end_time=end_time,
            count=-1,
            dividend_type='front_ratio',
            fill_data=True
        )

        df_list = []
        for field, df in market_data.items():
            df['stock_code'] = field
            df.index.name = 'date'
            df_list.append(df)
        combined_df = pd.concat(df_list, axis=0)
        return combined_df
    except Exception as e:
        logger.error(f"获取股票数据失败，错误信息：{e}")
        return pd.DataFrame()  # 返回空的 DataFrame 以防止后续代码崩溃


def save_data_to_csv(df, filename):
    """
    将数据保存到CSV文件中。

    :param df: 数据 DataFrame
    :param filename: 文件名
    """
    try:
        df.to_csv(filename)
        logger.info(f'数据已保存到 {filename}')
    except Exception as e:
        logger.error(f"保存数据失败，错误信息：{e}")


def download_and_save_xt_date(period='1d', start_time=None, end_time=None, callback=None):
    download_stock_data(period=period, start_time=start_time, end_time=end_time, callback=callback)
    combined_df = get_stock_data_as_dataframe(period=period, start_time=start_time, end_time=end_time)

    if not combined_df.empty:
        logger.info("Combined data:")

        now = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = Path(__file__).parent.parent / f'assets/data/combined_{period}_data_{now}.csv'
        save_data_to_csv(combined_df, filename=filename)
    else:
        logger.warning("未获取到任何数据，未保存到 CSV 文件。")
    return combined_df


if __name__ == '__main__':
    import schedule
    import time

    today = datetime.now().date()

    schedule.every().day.at("10:00").do(download_and_save_xt_date)
    schedule.every().day.at("11:00").do(download_and_save_xt_date)
    schedule.every().day.at("11:29").do(download_and_save_xt_date)

    download_and_save_xt_date()

    while True:
        if datetime.now().date() != today:
            break
        schedule.run_pending()
        time.sleep(1)
