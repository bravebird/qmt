import xtquant.xtdata as xtdata
import datetime
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 加载字体
font_path = 'assets/sider-font/微软雅黑.ttf'
font_prop = fm.FontProperties(fname=font_path)

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

# 获取本地数据方法
def get_local_data(stock_codes, period='1d', start_time='20200101', end_time=end_time):
    data_frames = []
    try:
        local_data_dict = xtdata.get_local_data(
            field_list=[],
            stock_list=stock_codes,
            period=period,
            start_time=start_time,
            end_time=end_time,
            count=-1,
            dividend_type='none',
            fill_data=True
        )

        for code in stock_codes:
            local_data = local_data_dict.get(code)
            if local_data is not None and not local_data.empty:
                data_with_code = local_data.copy()
                data_with_code['code'] = code  # 添加股票代码字段
                data_frames.append(data_with_code)
                logger.info(f"Data fetched for {code}: {local_data.head()}")
            else:
                logger.warning(f"No data or empty data for {code}")
    except Exception as e:
        logger.error(f"Error fetching local data: {e}")

    if data_frames:
        combined_data = pd.concat(data_frames, ignore_index=True)
        logger.info("Data combined successfully.")
    else:
        combined_data = pd.DataFrame()
        logger.warning("No data to combine.")

    return combined_data

# 获取数据
combined_data = get_local_data(stock_codes)

# 展示数据
logger.info("Displaying data head:")
print(combined_data.head())

# 保存到CSV文件
csv_output_path = 'assets/data/combined_data.csv'
combined_data.to_csv(csv_output_path, index=False)
logger.info(f"Combined data saved to {csv_output_path}")

# 可视化
if not combined_data.empty:
    plt.figure(figsize=(10, 6))
    for code in stock_codes:
        subset = combined_data[combined_data['code'] == code]
        plt.plot(subset['time'], subset['close'], label=code)

    plt.xlabel('Date', fontproperties=font_prop)
    plt.ylabel('Close Price', fontproperties=font_prop)
    plt.title('Stock Prices', fontproperties=font_prop)
    plt.legend(prop=font_prop)
    plt.show()
    logger.info("Plot displayed successfully.")
else:
    logger.warning("No data to plot")

if __name__ == '__main__':
    logger.info("Script executed successfully.")