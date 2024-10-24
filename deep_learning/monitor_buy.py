import os
import pathlib
import sys
import time
import traceback
import math
from datetime import datetime
from darts.models import TSMixerModel
from xtquant import xtconstant
from pathlib2 import Path
from apscheduler.executors.pool import ProcessPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from tzlocal import get_localzone
from xtquant import xtdata

# 提权
os.environ.update({"__COMPAT_LAYER": "RunAsInvoker"})

# 导入自定义API
path = pathlib.Path(__file__).parent.parent
os.chdir(str(path.absolute()))
if str(path) not in sys.path:
    sys.path.insert(0, str(path))

from deep_learning.tsmixer import get_training_data
from utils.utils_data import get_max_ask_price
from utils.utils_general import is_trading_day
from trader.xt_acc import acc
from trader.xt_trader import xt_trader, setup_xt_trader
from loggers import logger

# 设置最大持仓数
MAX_POSITIONS = 3


def buy_stock_async(stocks, strategy_name='', order_remark=''):
    """
    买入股票函数：根据股票代码后缀确定所属市场并设置 order_type 后，异步发出买入指令。
    """

    for i in range(15):
        xt_trader = setup_xt_trader()
        asset = xt_trader.query_stock_asset(acc)
        if asset is not None:
            break
        else:
            logger.warning(f"xt_trader.query_stock_asset返回值为None")
            time.sleep(1)

    if asset is None:
        logger.error(f"xt_trader.query_stock_asset返回值为None")

    cash = asset.cash
    positions = xt_trader.query_stock_positions(acc)
    positions_stocks = [pos.stock_code for pos in positions]
    set1 = set(stocks)
    set2 = set(positions_stocks)
    # 求差集
    difference = set1 - set2
    # 将结果转换回列表（如果需要）
    stocks = list(difference)

    position_list = [pos.stock_code for pos in positions if pos.volume > 0]
    position_count = len(position_list)
    available_slots = max(MAX_POSITIONS - position_count, 0)
    available_slots = min(available_slots, len(stocks))
    logger.info(f"available_slots: {available_slots}")
    if available_slots == 0:
        logger.info(f"当前持仓已满:{position_list}。")
        return False

    # if len(stocks) > available_slots:
    #     stocks = stocks[:available_slots]

    # for stock in stocks:
    #     xtdata.subscribe_quote(stock, period="l2quote", count=-1)
    # time.sleep(2)

    for stock_code in stocks:
        if stock_code.endswith('.SH') or stock_code.endswith('.SZ'):
            order_type = xtconstant.FIX_PRICE
        else:
            order_type = xtconstant.FIX_PRICE

        logger.info(f"股票【{stock_code}】报价类型为：{order_type}")

        # 读取最高要价
        max_ask_price = get_max_ask_price(stock_code)

        if max_ask_price == 999999:
            logger.warning(f"股票已经涨停：{stock_code}")
            continue

        if not max_ask_price:
            logger.warning(f"未能获得股票数据：{stock_code}")
            continue

        if max_ask_price == 0:
            logger.warning(f"委卖价为0，请检查{stock_code}的数据。")
            continue

        quantity = math.floor(cash / max_ask_price / available_slots / 100) * 100
        if quantity < 100:
            logger.info(f"{stock_code} 可买数量不足，现金：{cash}, 当前股价：{max_ask_price}")
            continue

        # response = xt_trader.order_stock_async(acc, stock_code, xtconstant.STOCK_BUY, quantity, order_type,
        #                                        max_ask_price,
        #                                        strategy_name, order_remark)
        response = xt_trader.order_stock(
            account=acc,
            stock_code=stock_code,
            order_type=xtconstant.STOCK_BUY,
            order_volume=quantity,
            price_type=order_type,
            price=max_ask_price,
            strategy_name=strategy_name,
            order_remark=order_remark
        )
        if response < 0:
            logger.trader(f'\n【提交下单失败！- 买入 - {strategy_name}】\n 股票【{stock_code}】，\n数量【{quantity}】，\n单价【{max_ask_price}】，\n金额【{quantity*max_ask_price}】，\n返回值【{response}】')
        else:
            logger.trader(f'\n【提交下单成功！- 买入 - {strategy_name}】\n 股票【{stock_code}】，\n数量【{quantity}】，\n单价【{max_ask_price}】，\n金额【{quantity*max_ask_price}】，\n返回值【{response}】')


def trading_with_fitted_model():
    """
    读入训练好的神经网络模型并生成交易列表。
    """
    logger.info("开始执行交易策略。")
    model_path = Path(__file__).parent.parent / './assets/models/tsmixer_model.pth.pkl'
    logger.info(model_path)

    try:
        model = TSMixerModel.load(str(model_path))
        logger.info("模型加载成功。")

        train, val, past_cov_ts, future_cov_ts, scaler_train = get_training_data(training_or_predicting='predicting')

        prediction = model.predict(n=3, series=train, past_covariates=past_cov_ts, future_covariates=future_cov_ts)

        result = scaler_train.inverse_transform(prediction)
        df = result.pd_dataframe()
        logger.info("预测结果已生成。")

        result = df.iloc[0, :].sort_values(ascending=False) * 100
        to_buy = result[result > 0.2].index.to_list()

        logger.trader(f"》》》》买入列表：{to_buy}")


        buy_stock_async(to_buy, strategy_name='tsmixer策略', order_remark='tsmixer策略买入。')


    except Exception as e:
        logger.error(f"交易执行过程中出现错误：{str(e)}")
        logger.error(traceback.format_exc())


def conditionally_execute_trading(test=False):
    """
    根据是否为交易日决定是否执行交易策略。
    """
    if is_trading_day() or test:
        trading_with_fitted_model()
    else:
        logger.info("今天不是交易日，交易策略未执行。")


def schedule_trading_job():
    """
    配置并启动计划任务调度器。
    """
    local_tz = get_localzone()
    executors = {
        'default': ProcessPoolExecutor(1)
    }

    job_defaults = {
        'misfire_grace_time': 300,
        'coalesce': False,
        'max_instances': 30
    }

    scheduler = BackgroundScheduler(executors=executors, job_defaults=job_defaults, timezone=local_tz)
    now = datetime.now()
    scheduler.add_job(conditionally_execute_trading, 'cron', day_of_week='mon-fri', hour=13, minute=3,
                      next_run_time=now)
    scheduler.add_job(conditionally_execute_trading, 'cron', day_of_week='mon-fri', hour=14, minute=59)
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
