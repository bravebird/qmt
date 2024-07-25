import pandas as pd
import numpy as np
from darts import TimeSeries
from darts.dataprocessing.transformers import Scaler
from darts.models import NBEATSModel, TSMixerModel
from sklearn.metrics import mean_squared_error
from xtquant import xtdata
from pathlib2 import Path
from pickle import dump, load
import joblib
import torch
import os
from datetime import datetime
# 自定义部分
from data.xt_data_download import download_get_and_save_kline_date
from loggers import logger
from deep_learning.model_config import ModelParameters


def get_training_data(training_or_predicting='training'):
    # 1. 下载数据
    data = download_get_and_save_kline_date()

    # 2. 清洗数据
    def group_clean_data(df):
        # 前向填充
        df = (df.ffill().bfill()).reset_index(drop=True)
        df.fillna(0, inplace=True)
        # 增加时间的整数序列
        df = df.reset_index(drop=True)
        df['time'] = df.index
        return df

    data = data.reset_index(drop=False)
    # 向前填充数据。
    data = data.groupby('stock_code').apply(group_clean_data)
    # 隔夜收益率
    data['overnight_return'] = data['close'] / data['preClose'] - 1
    # 异常值Na、inf等的处理，clip
    logger.debug("data准备就绪。")
    # 3. 生成TimeSeries
    # 3.1 预测目标train
    target_df = data.pivot(index="time", columns="stock_code", values='overnight_return')
    # 3.2 过去协变量past_covariates
    past_cov_df = data.pivot(index="time", columns="stock_code", values=['open', 'high', 'low', 'close', 'volume'])
    past_cov_df.columns = ["_".join(list(c)) for c in past_cov_df.columns]
    # 添加滞后项
    dfs = [past_cov_df]
    for i in [3, 5, 15, 30, 60]:
        df = past_cov_df.pct_change(periods=i)
        df.bfill(axis=0, inplace=True)
        dfs.append(df)
    past_cov_df = pd.concat(dfs, axis=1)
    past_cov_df.bfill(axis=0, inplace=True)
    past_cov_df.replace(np.inf, 0, inplace=True)
    logger.debug("past_cov_df准备就绪。")
    # 3.3 未来协变量future_covariates
    # 获取交易日历
    max_past_date = data['date'].max()
    end_time = str(int(max_past_date) + 10000)
    future_date = xtdata.get_trading_calendar("SH", start_time=max_past_date, end_time=end_time)
    ts = np.concatenate((data['date'].unique(), future_date[1:]))
    ts = pd.DatetimeIndex(ts)
    ts = ts.floor("D")
    future_cov_df = pd.DataFrame(
        # index=ts,
        data={
            'month_sin': np.sin(2 * np.pi * ts.month / 12),
            # 'month_cos': np.cos(2 * np.pi * ts.month / 12),
            'week_sin': np.sin(2 * np.pi * (ts.isocalendar().week / 53)),
            # 'week_cos': np.cos(2 * np.pi * ts.isocalendar().week / 53),
            'weekday_sin': np.sin(2 * np.pi * ts.weekday / 4),
            # 'weekday_cos': np.cos(2 * np.pi * ts.weekday / 4),
            "day": np.sin(2 * np.pi * ts.day / 31)
        },
    )
    future_cov_df = future_cov_df.reset_index(drop=True)
    logger.debug("future_cov_df准备就绪")
    # 3.4 静态协变量static_covariates
    # 暂无。
    # 4. 数据标准化。
    target_ts = TimeSeries.from_dataframe(target_df)
    target_ts = target_ts.astype(np.float32)
    past_cov_ts = TimeSeries.from_dataframe(past_cov_df)
    past_cov_ts = past_cov_ts.astype(np.float32)
    future_cov_ts = TimeSeries.from_dataframe(future_cov_df)
    future_cov_ts = future_cov_ts.astype(np.float32)

    if training_or_predicting == 'training':
        train, val = target_ts.split_after(0.92)
        scaler_train = Scaler(name='train').fit(train)
        scaler_past = Scaler(name='past').fit(past_cov_ts)
        dump(scaler_train, open('./assets/runtime/scaler_train.pkl', 'wb'))
        dump(scaler_past, open('./assets/runtime/scaler_past.pkl', 'wb'))
    elif training_or_predicting == 'predicting':
        train = target_ts
        _, val = target_ts.split_after(0.92)
        scaler_train = load(open(Path(__file__).parent.parent / 'assets/runtime/scaler_train.pkl', 'rb'))
        scaler_past = load(open(Path(__file__).parent.parent / 'assets/runtime/scaler_past.pkl', 'rb'))
    else:
        raise ValueError("training_or_predicting must be 'training' or 'predicting'")

    train = scaler_train.transform(train)
    val = scaler_train.transform(val)
    past_cov_ts = scaler_past.transform(past_cov_ts)

    return train, val, past_cov_ts, future_cov_ts, scaler_train


if __name__ == '__main__':
    train, val, past_cov_ts, future_cov_ts, scaler_train = get_training_data()

    # 5. 准备模型
    model = TSMixerModel(
        **vars(ModelParameters()),
        model_name="tsm"
    )

    # 6. 训练模型
    model.fit(
        # 训练集
        series=train,
        past_covariates=past_cov_ts,
        future_covariates=future_cov_ts,
        # 验证集
        val_series=val,
        val_past_covariates=past_cov_ts,
        val_future_covariates=future_cov_ts,
    )

    # 保存模型
    model.save('./assets/models/tsmixer_model.pth.pkl')

    # 评估模型
