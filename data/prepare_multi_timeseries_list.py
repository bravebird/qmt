import numpy as np
from darts.dataprocessing.transformers import Scaler
from pickle import dump, load

# 自定义库
from .mytimeseries import MyTimeSeries
from .prepare_combined_timeseries import fetch_and_clean_data, generate_future_covariates
from .data_config import config


def generate_time_series(clean_df):
    """
    生成目标时间序列和过去协变量时间序列。

    返回：
        tuple: 包含目标时间序列列表和过去协变量时间序列列表。
    """

    def create_series(value_cols):
        return MyTimeSeries.from_group_dataframe(
            df=clean_df,
            group_cols=['stock_code'],
            time_col='time',
            value_cols=value_cols,
            static_cols=['static_cov'],
            freq=1,
            verbose=True,
            drop_group_cols=['stock_code'],
        )

    targets_ts_list = create_series(['overnight_return'])

    values_columns = [ 'open', 'high', 'low', 'close', 'amount',
                      'open_lag_3', 'close_lag_3', 'amount_lag_3',
                      'open_lag_5', 'close_lag_5', 'amount_lag_5', 'open_lag_10',
                      'close_lag_10', 'amount_lag_10', 'open_lag_20', 'close_lag_20',
                      'amount_lag_20', 'open_lag_60', 'close_lag_60', 'amount_lag_60',
                      'open_pct_change', 'close_pct_change', 'amount_pct_change', 'mean_open',
                      'mean_high', 'mean_low', 'mean_close', 'mean_amount', 'ma_7', 'ma_14',
                      'ma_21', 'ema_12', 'ema_26', 'ema_3', 'ema_5', 'rsi_14',
                      'rolling_max_high_14', 'rolling_min_low_14']
    past_cov_ts_list = create_series(values_columns)

    # 转换数据类型为 float32
    targets_ts_list = [ts.astype(np.float32) for ts in targets_ts_list]
    past_cov_ts_list = [ts.astype(np.float32) for ts in past_cov_ts_list]

    return targets_ts_list, past_cov_ts_list


def validate_alignment(targets_ts_list, past_cov_ts_list):
    """
    验证目标序列和过去协变量序列是否对齐。

    抛出：
        ValueError: 如果序列未对齐。
    """
    for target_ts, past_cov_ts in zip(targets_ts_list, past_cov_ts_list):
        if target_ts.static_covariates_values()[0][0] != past_cov_ts.static_covariates_values()[0][0]:
            raise ValueError("目标序列和过去协变量序列未对齐，请检查数据。")


def split_data(data_list, header_length, val_length, test_length):
    """
    根据配置分割数据。

    返回：
        tuple: 包含训练集、验证集和测试集的数据集。
    """
    train_list = [ts[header_length:-(val_length + test_length)] for ts in data_list]
    val_list = [ts[-(val_length + test_length + header_length):-test_length] for ts in data_list]
    test_list = [ts[-(test_length + header_length):] for ts in data_list]

    return train_list, val_list, test_list


def get_or_transform_scaler(data_list, save_path, operation_mode):
    """
    获取或拟合并保存标准化对象。

    参数：
        operation_mode (str): 'training' 进行拟合，'predicting' 加载现有标准化对象。

    返回：
        Scaler: 标准化对象。
    """
    if operation_mode not in ['training', 'predicting']:
        raise ValueError("operation_mode 必须是 'training' 或 'predicting'")

    if operation_mode == 'training':
        scaler = Scaler().fit(data_list)
        with open(save_path, 'wb') as f:
            dump(scaler, f)
    else:  # predicting
        with open(save_path, 'rb') as f:
            scaler = load(f)

    return scaler


def process_and_save_series(targets_ts_list, past_cov_ts_list, future_cov_ts, operation_mode):
    """
    处理并将序列数据保存到指定路径。

    返回：
        dict: 包含数据集和标准化对象的字典。
    """
    header_length = config['set_length']['header_length']
    val_length = config['set_length']['val_length']
    test_length = config['set_length']['test_length']

    train_list, val_list, test_list = split_data(targets_ts_list, header_length, val_length, test_length)

    target_scaler = get_or_transform_scaler(train_list, config['data_save_paths']['scaler_train'], operation_mode)
    past_cov_scaler = get_or_transform_scaler(past_cov_ts_list, config['data_save_paths']['scaler_past'],
                                              operation_mode)

    # 应用标准化变换
    transform = lambda lst, scaler: scaler.transform(lst)
    train_list = transform(train_list, target_scaler)
    val_list = transform(val_list, target_scaler)
    test_list = transform(test_list, target_scaler)
    past_cov_ts_list = transform(past_cov_ts_list, past_cov_scaler)
    future_cov_ts_list = [future_cov_ts] * len(train_list)

    save_time_series_data(train_list, val_list, test_list, past_cov_ts_list, future_cov_ts_list)

    return {
        'train': train_list,
        'val': val_list,
        'test': test_list,
        'past_cov': past_cov_ts_list,
        'future_cov': future_cov_ts_list,
        'target_scaler': target_scaler,
        'past_cov_scaler': past_cov_scaler
    }


def save_time_series_data(train_list, val_list, test_list, past_cov_ts_list, future_cov_ts_list):
    """
    将时间序列数据保存到文件。
    """
    data_path = config['data_path']
    data_save_paths = config['data_save_paths']

    def save(data, path):
        """将数据保存到指定路径"""
        with open(path, 'wb') as file:
            dump(data, file)

    save(train_list, data_path / data_save_paths['train'])
    save(val_list, data_path / data_save_paths['val'])
    save(test_list, data_path / data_save_paths['test'])
    save(past_cov_ts_list, data_path / data_save_paths['past_cov'])
    save(future_cov_ts_list, data_path / data_save_paths['future_cov'])


def prepare_multi_timeseries_list(mode):
    """
    主要功能，生成并保存时间序列数据。

    返回：
        dict: 数据集和标准化对象。
    """
    clean_df = fetch_and_clean_data()
    targets_ts_list, past_cov_ts_list = generate_time_series(clean_df)
    validate_alignment(targets_ts_list, past_cov_ts_list)
    future_cov_ts = generate_future_covariates(clean_df)

    return process_and_save_series(targets_ts_list, past_cov_ts_list, future_cov_ts, mode)