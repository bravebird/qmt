import pandas as pd
from pathlib import Path
from joblib import dump, load
from darts import TimeSeries
from darts.dataprocessing.transformers import Scaler
import numpy as np
from sklearn.preprocessing import MinMaxScaler
# import logging
# 自定义
from loggers import logger
from data.xt_data_download import download_history_data


def forward_fill_data(df):
    """
    前向和后向填充缺失数据，并重设索引。
    @param df: 需要填充的数据 DataFrame。
    @return: 填充后的 DataFrame。
    """
    df = (df.ffill().bfill()).reset_index(drop=True)
    df.fillna(0, inplace=True)
    return df


def add_time_sequence(df):
    """
    为数据添加时间序列。
    @param df: 数据 DataFrame。
    @return: 添加时间序列后的 DataFrame。
    """
    df.sort_values(by='time', ascending=True, inplace=True)
    df = df.reset_index(drop=True)
    df['time'] = df.index
    df.index.name = 'time_seq'
    return df


def calculate_overnight_return(data):
    """
    计算隔夜收益率。
    @param data: 数据 DataFrame，必须包含 'close' 和 'preClose' 列。
    @return: 包含隔夜收益率的 DataFrame。
    """
    data['overnight_return'] = data['close'] / data['preClose'] - 1
    data.fillna(0, inplace=True)
    return data


def clean_data(data):
    """
    清洗数据，包括前向填充、添加时间序列和计算隔夜收益率等操作。
    @param data: 原始数据 DataFrame。
    @return: 清洗后的数据 DataFrame。
    """
    # data = data.reset_index(drop=False)
    # data = data.groupby('stock_code', include_groups=False).apply(forward_fill_data)
    # data = data.groupby('stock_code', include_groups=False).apply(add_time_sequence)
    # data = calculate_overnight_return(data)
    # return data
    data = data.reset_index(drop=False)
    data = data.groupby('stock_code').apply(forward_fill_data, include_groups=False)
    data = data.groupby('stock_code').apply(add_time_sequence, include_groups=False)
    data = calculate_overnight_return(data)
    data.reset_index(inplace=True)
    return data


def generate_target_ts(data):
    """
    生成目标时间序列。
    @param data: 清洗后的数据 DataFrame。
    @return: 目标 TimeSeries 对象。
    """
    target_df = data.pivot(index="time", columns="stock_code", values='overnight_return')
    return TimeSeries.from_dataframe(target_df)


def generate_past_cov_ts(data):
    """
    生成过去协变量时间序列。
    @param data: 清洗后的数据 DataFrame。
    @return: 过去协变量 TimeSeries 对象。
    """
    past_cov_df = data.pivot(index="time", columns="stock_code", values=['open', 'high', 'low', 'close', 'volume'])
    past_cov_df.columns = ["_".join(list(c)) for c in past_cov_df.columns]

    dfs = [past_cov_df]
    for i in [3, 5, 15, 30, 60]:
        df = past_cov_df.pct_change(periods=i)
        df.bfill(axis=0, inplace=True)
        dfs.append(df)
    past_cov_df = pd.concat(dfs, axis=1)
    past_cov_df.bfill(axis=0, inplace=True)
    past_cov_df.replace(np.inf, 0, inplace=True)

    return TimeSeries.from_dataframe(past_cov_df)


def generate_future_cov_ts(future_dates):
    """
    生成未来协变量时间序列。
    @param data: 清洗后的数据 DataFrame。
    @param future_dates: 未来交易日期列表。
    @return: 未来协变量 TimeSeries 对象。
    """
    ts = pd.DatetimeIndex(future_dates)
    # ts = ts.floor("D")
    future_cov_df = pd.DataFrame(
        data={
            'month_sin': np.sin(2 * np.pi * ts.month / 12),
            'month_cos': np.cos(2 * np.pi * ts.month / 12),
            'week_sin': np.sin(2 * np.pi * (ts.isocalendar().week / 53)),
            'week_cos': np.cos(2 * np.pi * (ts.isocalendar().week / 53)),
            'weekday_sin': np.sin(2 * np.pi * ts.weekday / 4),
            'weekday_cos': np.cos(2 * np.pi * ts.weekday / 4),
            "day_sin": np.sin(2 * np.pi * ts.day / 31),
            "day_cos": np.cos(2 * np.pi * ts.day / 31)
        },
    )
    future_cov_df = future_cov_df.reset_index(drop=True)
    return TimeSeries.from_dataframe(future_cov_df)


def get_future_dates(data, xtdata):
    """
    获取未来交易日期。
    @param data: 清洗后的数据 DataFrame。
    @param xtdata: 交易日期数据源对象。
    @return: 未来交易日期列表。
    """
    max_past_date = data['date'].max()
    end_time = str(int(max_past_date) + 10000)
    future_dates = xtdata.get_trading_calendar("SH", start_time=max_past_date, end_time=end_time)
    return np.concatenate((data['date'].unique(), future_dates[1:])).sort()


def load_scaler(path):
    """
    加载数据归一化器。
    @param path: 归一化器文件路径。
    @return: 加载的归一化器对象。
    """
    try:
        with open(path, 'rb') as f:
            return load(f)
    except EOFError:
        logger.error(f"Failed to load scaler: {path} is incomplete or corrupted.")
        return None


def save_scaler(scaler, path):
    """
    保存数据归一化器。
    @param scaler: 归一化器对象。
    @param path: 保存路径。
    """
    dump(scaler, open(path, 'wb'))


def standardize_data(target_ts, past_cov_ts, future_cov_ts, start_index, training_or_predicting, path_scaler_train,
                     path_scaler_past):
    """
    数据标准化。
    @param target_ts: 目标 TimeSeries。
    @param past_cov_ts: 过去协变量 TimeSeries。
    @param future_cov_ts: 未来协变量 TimeSeries。
    @param start_index: 开始索引位置。
    @param training_or_predicting: 'training' 或 'predicting'，指示当前是训练还是预测。
    @param path_scaler_train: 训练集归一化器的文件路径。
    @param path_scaler_past: 过去协变量归一化器的文件路径。
    @return: 标准化后的训练数据, 验证数据, 过去协变量, 未来协变量以及归一化器。
    """
    target_ts = target_ts[start_index:]
    past_cov_ts = past_cov_ts[start_index:]
    future_cov_ts = future_cov_ts[start_index:]

    target_ts = target_ts.astype(np.float32)
    past_cov_ts = past_cov_ts.astype(np.float32)
    future_cov_ts = future_cov_ts.astype(np.float32)

    scaler_train, scaler_past = None, None

    if training_or_predicting == 'training':
        train, val = target_ts[:-60], target_ts[-80:]
        scaler_train = Scaler().fit(train)
        scaler_past = Scaler().fit(past_cov_ts)
        save_scaler(scaler_train, path_scaler_train)
        save_scaler(scaler_past, path_scaler_past)
    elif training_or_predicting == 'predicting':
        train, val = target_ts, target_ts[-80:]
        scaler_train = load_scaler(path_scaler_train)
        scaler_past = load_scaler(path_scaler_past)
    else:
        raise ValueError("training_or_predicting must be 'training' or 'predicting'")

    train = scaler_train.transform(train)
    val = scaler_train.transform(val)
    past_cov_ts = scaler_past.transform(past_cov_ts)

    return train, val, past_cov_ts, future_cov_ts, scaler_train


def get_training_data(training_or_predicting='training', xtdata=None):
    """
    主函数：下载、清洗数据并生成 TimeSeries 对象和归一化数据。
    @param training_or_predicting: 'training' 或 'predicting'，指示当前是训练还是预测。
    @param xtdata: 交易日期数据源对象。
    @return: 标准化后的训练数据, 验证数据, 过去协变量, 未来协变量以及归一化器。
    """
    # 1. 下载数据
    data = download_history_data()

    # 2. 清洗数据
    data = clean_data(data)
    logger.debug("data准备就绪。")

    # 3. 生成TimeSeries
    target_ts = generate_target_ts(data)
    past_cov_ts = generate_past_cov_ts(data)
    logger.debug("past_cov_df准备就绪。")

    # 获取交易日历
    future_dates = get_future_dates(data, xtdata)
    future_cov_ts = generate_future_cov_ts(future_dates)
    logger.debug("future_cov_df准备就绪")

    # 获取文件路径
    path_scaler_train = str(Path(__file__).parent.parent / 'assets/runtime/scaler_train.pkl')
    path_scaler_past = str(Path(__file__).parent.parent / 'assets/runtime/scaler_past.pkl')

    # 4. 数据标准化
    start_index = target_ts.time_index[-1000]
    train, val, past_cov_ts, future_cov_ts, scaler_train = standardize_data(
        target_ts, past_cov_ts, future_cov_ts, start_index, training_or_predicting, path_scaler_train, path_scaler_past
    )

    return train, val, past_cov_ts, future_cov_ts, scaler_train


from sklearn.preprocessing import MinMaxScaler


def rbf(x, centers, width):
    """径向基函数计算"""
    return np.exp(-((x[:, None] - centers[None, :]) ** 2) / (2 * width ** 2))


def rbf_encode_time_features(dates, num_centers=10):
    """
    使用径向基函数对 day、weekday、month、week 进行编码。

    参数：
    dates (pd.Series): 日期序列。
    num_centers (int): RBF 中心数量。

    返回：
    pd.DataFrame: 编码后的特征矩阵。
    """
    # 提取时间特征
    days = dates.day
    weekdays = dates.weekday  # Monday=0, Sunday=6
    months = dates.month
    weeks = dates.isocalendar().week

    # 归一化时间特征到[0, 1]区间
    scaler = MinMaxScaler()
    days_scaled = scaler.fit_transform(days.values.reshape(-1, 1)).flatten()
    weekdays_scaled = scaler.fit_transform(weekdays.values.reshape(-1, 1)).flatten()
    months_scaled = scaler.fit_transform(months.values.reshape(-1, 1)).flatten()
    weeks_scaled = scaler.fit_transform(weeks.values.reshape(-1, 1)).flatten()

    # 为每个特征创建 RBF 中心和宽度
    day_centers = np.linspace(0, 1, num_centers)
    weekday_centers = np.linspace(0, 1, num_centers)
    month_centers = np.linspace(0, 1, num_centers)
    week_centers = np.linspace(0, 1, num_centers)

    width = 1.0 / num_centers

    # 计算 RBF 编码
    day_rbf = rbf(days_scaled, day_centers, width)
    weekday_rbf = rbf(weekdays_scaled, weekday_centers, width)
    month_rbf = rbf(months_scaled, month_centers, width)
    week_rbf = rbf(weeks_scaled, week_centers, width)

    # 组合成特征矩阵
    encoded_features = np.hstack([day_rbf, weekday_rbf, month_rbf, week_rbf])

    return pd.DataFrame(encoded_features)
