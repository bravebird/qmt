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
os.environ.update({"__COMPAT_LAYER": "RunAsInvoker"})

# 导入自定义API
path = pathlib.Path(__file__).absolute().parent
os.chdir(path)
if str(path) not in sys.path:
    sys.path.insert(0, str(path))

from deep_learning.tsmixer import get_training_data
from trader.xt_acc import acc
from trader.xt_trader import xt_trader
from trader.xt_data import xt_data
from loggers import logger

# 设置最大持仓数
MAX_POSITIONS = 2


def buy_stock_async(stocks, strategy_name='', order_remark=''):
    """
    买入股票函数：根据股票代码后缀确定所属市场并设置 order_type 后，异步发出买入指令。
    """
    if len(stocks) > MAX_POSITIONS:
        stocks = stocks[:MAX_POSITIONS]

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

        logger.info(f"股票【{stock_code}】报价类型为：{order_type}")

        asset = xt_trader.query_stock_asset(acc)
        positions = xt_trader.query_stock_positions(acc)
        position_count = len([pos.stock_code for pos in positions if pos.volume > 0])
        available_slots = max(MAX_POSITIONS - position_count, 0)

        if available_slots == 0:
            logger.info("当前持仓已满。")
            continue

        cash = asset.cash
        now = datetime.now().strftime("%Y%m%d%H%M%S")
        market_data = xt_data.get_market_data(stock_list=[stock_code], period='tick', start_time=now)

        if not market_data.get(stock_code):
            logger.warning(f"未能获得股票数据：{stock_code}, 时间：{now}")
            continue

        price = market_data[stock_code][-1].get('askPrice')
        if price == 0:
            logger.warning(f"委卖价为0，请检查{stock_code}的数据。")
            continue

            # 计算可买数量，向上取整成100的倍数
        quantity = math.ceil(cash / price / available_slots / 100) * 100
        if quantity <= 100:
            logger.info(f"{stock_code} 可买数量不足，现金：{cash}, 当前股价：{price}")
            continue

        response = xt_trader.order_stock_async(acc, stock_code, xtconstant.STOCK_BUY, quantity, order_type, price,
                                               strategy_name, order_remark)
        logger.info(f'买入股票【{stock_code}】，数量【{quantity}】，返回值【{response}】')

        # 更新持仓信息
    positions = xt_trader.query_stock_positions(acc)
    logger.info("更新持仓信息完成")


def trading_with_fitted_model():
    """
    读入训练好的神经网络模型并生成交易列表。
    """
    logger.info("开始执行交易策略。")

    try:
        # 加载模型
        model = TSMixerModel.load('./assets/models/tsmixer_model.pth.pkl')
        logger.info("模型加载成功。")

        # 准备数据
        train, val, past_cov_ts, future_cov_ts, scaler_train = get_training_data(training_or_predicting='predicting')

        # 模型预测
        prediction = model.predict(n=3, series=train, past_covariates=past_cov_ts, future_covariates=future_cov_ts)

        # 反转缩放并生成预测结果
        result = scaler_train.inverse_transform(prediction)
        df = result.pd_dataframe()
        logger.info("预测结果生成。")
        logger.info(df)

        result = df.iloc[0, :].sort_values(ascending=False) * 100
        to_buy = result[result > 0.2].index.to_list()
        logger.info(f"》》》》买入列表：{to_buy}")

        # 执行买入操作
        buy_stock_async(to_buy, strategy_name='tsmixer策略', order_remark='tsmixer策略买入。')

    except Exception as e:
        logger.error(f"交易执行过程中出现错误：{str(e)}")
        logger.error(traceback.format_exc())


def schedule_trading_job():
    """
    配置并启动计划任务调度器。
    """
    local_tz = get_localzone()
    executors = {
        'default': ProcessPoolExecutor(1)
    }
    scheduler = BackgroundScheduler(executors=executors, timezone=local_tz)
    scheduler.add_job(trading_with_fitted_model, 'cron', day_of_week='mon-fri', hour=14, minute=59)
    scheduler.start()
    logger.info("任务调度器已启动。")


if __name__ == '__main__':
    try:
        schedule_trading_job()
        logger.info("主程序正在运行。按 Ctrl+C 终止。")
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        logger.info("程序终止。")