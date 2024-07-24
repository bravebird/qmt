import os
import pathlib
import sys
import time
import traceback
import math
from datetime import datetime, timedelta
from darts.models import TSMixerModel
from xtquant import xtconstant, xttrader

import pandas as pd
from apscheduler.executors.pool import ProcessPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from tzlocal import get_localzone

# 提权
os.environ.update({"__COMPAT_LAYER": "RunAsInvoke"})
# 导入自定义api
path = pathlib.Path("__file__").absolute().parent
os.chdir(path)
print(path)
if str(path) not in sys.path:
    sys.path.insert(0, str(path))
from deep_learning.tsmixer import get_training_data
from trader.xt_acc import acc
from trader.xt_trader import xt_trader
from trader.xt_data import xt_data
from loggers import logger


def buy_stock_async(stocks, strategy_name='', order_remark=''):
    """
    卖出股票函数，根据股票代码后缀确定所属市场并设置order_type后，异步发出卖出指令。
    """
    # global positions
    max_positions = 2
    if len(stocks) > max_positions:
        stocks = stocks[:max_positions]
    for stock_code in stocks:
        if stock_code.endswith('.SH'):
            # 沪市：最优五档即时成交剩余撤销
            order_type = xtconstant.MARKET_SH_CONVERT_5_CANCEL
        elif stock_code.endswith('.SZ'):
            # 深市：最优五档即时成交剩余撤销
            order_type = xtconstant.MARKET_SZ_CONVERT_5_CANCEL
        else:
            # 其他市场，默认使用限价单
            order_type = 0
            # 发出卖出指令并打印响应信息
        logger.info(f"报价类型{order_type}")

        asset = xt_trader.query_stock_asset(acc)
        positions = xt_trader.query_stock_positions(acc)
        position_count = len([pos.stock_code for pos in positions if pos.volume > 0])
        nums = max(max_positions-position_count, 0)
        if nums == 0:
            logger.info(f"持仓数已经达到2只。")
            continue
        cash = asset.cash
        now = datetime.now().strftime("%Y%m%d%H%M%S")
        market_data = xt_data.get_market_data(stock_list=[stock_code],period='tick',start_time=now)
        if len(market_data[stock_code]) == 0:
            logger.warning(f"未能获得股票数据{stock_code},时间：{now}。")
            continue
        price = market_data[stock_code][-1]['askPrice']
        if price == 0:
            logger.warning("委卖价为0，请检查数据。")
            continue
        # 计算可买数量
        quantity = math.ceil(cash / price / nums / 100) * 100
        if quantity <= 100:
            logger.info(f"{stock_code}可买数量为0, 可用现金为{cash}, 当前股价为{price}。")
            continue

        response = xt_trader.order_stock_async(acc, stock_code, xtconstant.STOCK_BUY, quantity, order_type, price,
                                               strategy_name,
                                               order_remark)
        logger.log("TRADER", f'卖出股票【{stock_code}】，数量【{quantity}】，返回值为【 {response}】')
        # 更新持仓信息
    positions = xt_trader.query_stock_positions(acc)


def trading_with_fitted_model():
    """
    读入训练好的神经网络模型，生成交易列表。
    模型的参数，来自于BaseConfig对象，注意训练时时进行区分。
    """
    # 判断今天是否为交易日
    # if not (is_transaction_day() or test):
    #     logger.info("今天不是交易日")
    #     return "今天不是交易日"
    # logger.info("今天是交易日")
    # 1. 准备模型
    model = TSMixerModel.load('./assets/models/tsmixer_model.pth.pkl')
    # 2. 准备数据
    train, val, past_cov_ts, future_cov_ts, scaler_train = get_training_data(training_or_predicting='predicting')
    # 3.预测
    prediction = model.predict(
        n=3,
        # num_samples=500,
        series=train,
        past_covariates=past_cov_ts,
        future_covariates=future_cov_ts,
    )
    # 4. 预测结果
    result = scaler_train.inverse_transform(prediction)
    df = result.pd_dataframe()
    logger.info(df)

    result = df.iloc[0, :]
    result = result.sort_values(ascending=False) * 100
    to_buy = result[result > 0.2].index.to_list()
    to_sell = result[result < 0.2].index.to_list()
    logger.info(f"》》》》买入列表：{to_buy}---卖出列表：{to_sell}")
    buy_stock_async(to_buy, strategy_name='tsmixer策略', order_remark='tsmixer策略买入。')


if __name__ == '__main__':
    trading_with_fitted_model()
    # buy_stock_async('601838.SH',100, price=0, strategy_name='', order_remark='')

