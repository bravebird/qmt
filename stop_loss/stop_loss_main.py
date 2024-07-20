import csv  # 用于读取CSV文件
import pickle  # 用于序列化和反序列化Python对象
import time  # 用于获取当前时间
import os
from multiprocessing import Manager
from trader import xt_trader, acc
from xtquant import xtconstant
from xtquant import xtdata
from pathlib2 import Path
# 自定义模块
from loggers import logger  # 日志记录器
from utils.utils_data import get_targets_list_from_csv

# 初始化全局变量
max_profit = {}
positions = []


def save_max_profit(max_profit_file ='./assets/runtime/max_profit.pkl'):
    """
    保存最大收益率字典到Pickle文件
    """
    global max_profit
    global positions

    # 创建一个副本来保存需要删除的股票代码
    stocks_to_remove = []

    # 检查每只股票的持仓量，如果持仓量为 0，就添加到删除列表
    for pos in positions:
        if pos.can_use_volume == 0:
            stocks_to_remove.append(pos.stock_code)

            # 从 max_profit 字典中删除持仓量为 0 的股票
    for stock_code in stocks_to_remove:
        if stock_code in max_profit:
            del max_profit[stock_code]

            # 保存更新后的 max_profit 字典到 Pickle 文件
    try:
        with open(max_profit_file, 'wb') as f:
            pickle.dump(max_profit, f)
        logger.info(f"Max profit saved successfully to {max_profit_file}")
    except Exception as e:
        logger.error(f"Error saving max profit to Pickle file: {e}")


def load_max_profit(max_profit_file ='./assets/runtime/max_profit.pkl'):
    """
    从Pickle文件加载最大收益率字典
    """
    global max_profit

    try:
        with open(max_profit_file, 'rb') as f:
            max_profit = pickle.load(f)
        logger.info(f"Max profit loaded successfully from {max_profit_file}")
    except FileNotFoundError:
        max_profit = {}
        logger.warning(f"Max profit file not found: {max_profit_file}. Starting with an empty dictionary.")
    except Exception as e:
        logger.error(f"Error loading max profit from Pickle file: {e}")
        max_profit = {}


def sell_stock(stock_code, quantity, price=0, strategy_name='', order_remark=''):
    """
    卖出股票函数，根据股票代码后缀确定所属市场并设置order_type后，异步发出卖出指令。
    """
    global positions

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
    response = xt_trader.order_stock_async(acc, stock_code, xtconstant.STOCK_SELL, quantity, order_type, price,
                                           strategy_name,
                                           order_remark)
    logger.info(f'Sold {quantity} shares of {stock_code}. Response: {response}')
    # 更新持仓信息
    positions = xt_trader.query_stock_positions(acc)


def abs_stop_loss(datas):
    """
    绝对止损策略函数，如果当前收益率小于或等于-1%，则卖出股票。
    """
    global positions  # 声明使用全局变量 positions

    for pos in positions:
        stock_code = pos.stock_code
        volume = pos.can_use_volume
        avg_price = pos.avg_price

        if stock_code in datas:
            last_price = datas[stock_code]['lastPrice']
            if avg_price != 0:
                profit_rate = (last_price - avg_price) / avg_price

                if profit_rate <= -0.01:
                    sell_stock(stock_code, volume, 0, "止损策略", "收益率为-1%")  # 卖出可用数量


def stop_loss_max_profit(datas):
    """
    最大盈利超过0.5%且回撤幅度达到50%时的止损策略。
    """
    global positions  # 声明使用全局变量 positions
    global max_profit  # 声明使用全局变量 max_profit

    for pos in positions:
        stock_code = pos.stock_code
        volume = pos.can_use_volume
        avg_price = pos.avg_price

        if stock_code in datas:
            last_price = datas[stock_code]['lastPrice']
            if avg_price != 0:
                # 初始化最大盈利率
                if stock_code not in max_profit:
                    max_profit[stock_code] = (last_price - avg_price) / avg_price

                current_profit = (last_price - avg_price) / avg_price
                if max_profit[stock_code] < current_profit:
                    max_profit[stock_code] = current_profit
                    save_max_profit()

                # 判断回撤止损条件
                if max_profit[stock_code] > 0.005 and current_profit <= max_profit[stock_code] * 0.5:
                    sell_stock(stock_code, volume, 0, "止盈回撤策略", f"最大盈利超过0.5%，当前回撤至{current_profit}")


def stop_loss_large_profit(datas):
    """
    最大盈利超过20%且盈利回撤10个百分点时的止损策略。
    """
    global positions  # 声明使用全局变量 positions
    global max_profit  # 声明使用全局变量 max_profit

    for pos in positions:
        stock_code = pos.stock_code
        volume = pos.can_use_volume
        avg_price = pos.avg_price

        if stock_code in datas:
            last_price = datas[stock_code]['lastPrice']
            if avg_price != 0:
                # 初始化最大盈利率
                if stock_code not in max_profit:
                    max_profit[stock_code] = (last_price - avg_price) / avg_price

                current_profit = (last_price - avg_price) / avg_price
                if max_profit[stock_code] < current_profit:
                    max_profit[stock_code] = current_profit
                    save_max_profit()

                # 判断回撤止损条件
                if max_profit[stock_code] > 0.20 and current_profit <= max_profit[stock_code] - 0.10:
                    sell_stock(stock_code, volume, 0, "高盈利回撤策略", f"最大盈利超过20%，当前回撤至{current_profit}")


def call_back_functions(data, last_update_time):
    """
    数据回调函数，每次数据更新时调用，用于执行止损逻辑。
    """
    global positions  # 声明使用全局变量 positions
    current_time = time.time()

    # 如果离上次更新小于10分钟，就不执行更新
    if current_time - last_update_time.value >= 600:
        positions = xt_trader.query_stock_positions(acc)  # 查询最新持仓信息
        # 只保留可用股票余额大于0的持仓
        positions = [pos for pos in positions if pos.can_use_volume > 0]
        logger.info("更新持仓。")

        # 撤销未成交的订单
        pending_orders = xt_trader.query_stock_orders(acc)
        for order in pending_orders:
            if order.order_status == xtconstant.ORDER_PART_SUCC:
                cancel_response = xt_trader.cancel_order_stock_async(acc, order.order_id)
                logger.info(f"撤销订单 {order.order_id}。Response: {cancel_response}")

        last_update_time.value = current_time  # 更新上次更新时间

    abs_stop_loss(data)  # 执行绝对止损策略
    stop_loss_max_profit(data)  # 执行最大盈利回撤止损策略
    stop_loss_large_profit(data)  # 执行高盈利回撤止损策略


if __name__ == '__main__':
    manager = Manager()
    last_update_time = manager.Value('d', time.time())  # 使用Manager创建共享变量

    load_max_profit()  # 加载最大收益率
    positions = xt_trader.query_stock_positions(acc)  # 初始化positions
    stock_list = get_targets_list_from_csv()  # 从Pickle文件读取股票列表
    logger.info(stock_list)
    xtdata.subscribe_whole_quote(stock_list,
                                 callback=lambda data: call_back_functions(data, last_update_time))  # 订阅股票数据并设置回调函数
    xtdata.run()  # 启动数据接收和回调处理
