import pandas as pd
import numpy as np
from darts import TimeSeries
from darts.models import RNNModel
from darts.dataprocessing.transformers import Scaler
from darts.metrics import mape
import matplotlib.pyplot as plt
from darts.models import TSMixerModel
from matplotlib import font_manager as fm

font_path = 'assets/sider-font/微软雅黑.ttf'
font_prop = fm.FontProperties(fname=font_path)

from loggers import logger

combined_data_file_path = 'assets/data/combined_data.csv'
combined_data = pd.read_csv(combined_data_file_path)

# 将time列转化为整数列，不使用datetime格式
combined_data['time'] = pd.to_numeric(combined_data['time'], errors='coerce')

# 显示前几行以验证转换结果
print(combined_data.head())


# 将数据转换为darts的TimeSeries格式
series = TimeSeries.from_dataframe(combined_data, 'time', 'close', freq=None)

# 划分训练集和测试集
train_size = 0.8
train, val = series.split_after(train_size)

# 定义并训练TSMixerModel模型
model = TSMixerModel(input_chunk_length=30, output_chunk_length=1)
model.fit(train)

# 进行预测
predictions = model.predict(len(val))

# 可视化预测结果
import matplotlib.pyplot as plt

plt.figure(figsize=(10, 6))
series.plot(label='Actual')
predictions.plot(label='Predicted')
plt.xlabel('Time', fontproperties=font_prop)
plt.ylabel('Close Price', fontproperties=font_prop)
plt.title('TSMixerModel Predictions', fontproperties=font_prop)
plt.legend(prop=font_prop)
plt.show()

if __name__ == '__main__':
    pass