import xtquant.xtdata as xtdata
import datetime
import pandas as pd
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 读取CSV文件
file_path = 'assets/investment_targets/investment_targets.csv'
try:
    investment_targets = pd.read_csv(file_path)
    logger.info(f"Read CSV file from {file_path}")
except Exception as e:
    logger.error(f"Error reading CSV file from {file_path}: {e}")
    raise

# 获取当前时间
end_time = datetime.datetime.now().strftime('%Y%m%d')
logger.info(f"Current end_time set to {end_time}")

# 股票代码列表
try:
    stock_codes = investment_targets['SECURE'].tolist()
    logger.info(f"Stock codes extracted: {stock_codes}")
except KeyError as e:
    logger.error(f"Error extracting stock codes: {e}")
    raise

# 下载数据函数
def download_data(stock_codes, period='1d', start_time='20200101', end_time=end_time):
    logger.info("Starting data download...")
    for code in stock_codes:
        try:
            logger.info(f"Downloading data for {code}...")
            xtdata.download_history_data(
                stock_code=code,
                period=period,
                start_time=start_time,
                end_time=end_time,
                incrementally=False
            )
            logger.info(f"Data download completed for {code}.")
        except Exception as e:
            logger.error(f"Error downloading data for {code}: {e}")

# 下载数据
download_data(stock_codes)

def on_callback(data):
    print("data_call_back")
    print(data)

xtdata.download_history_data2(
    stock_codes,
    '1d',
    start_time='20200101',
    end_time=end_time,
    callback=on_callback,
    incrementally=False
)

if __name__ == '__main__':
    logger.info("Script executed successfully.")