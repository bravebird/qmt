# 导入必要的模块和函数
import csv  # 用于读取CSV文件
import time  # 用于获取当前时间
from trader import xt_trader, acc
from xtquant import xtconstant
from xtquant import xtdata
from loggers import logger

# 声明全局变量：持仓信息和最大收益率字典
positions = xt_trader.query_stock_positions(acc)
max_profit = {}
last_update_time = time.time()  # 记录上次更新持仓信息的时间


def sell_stock(stock_code, quantity, price=0, strategy_name='', order_remark=''):
    """
    卖出股票函数，根据股票代码后缀确定所属市场并设置order_type后，异步发出卖出指令。
    """
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
    response = xt_trader.order_stock_async(acc, stock_code, xtconstant.STOCK_SELL, quantity, order_type, price, strategy_name,
                                           order_remark)
    print(f'Sold {quantity} shares of {stock_code}. Response: {response}')


def abs_stop_loss(datas):
    """
    绝对止损策略函数，如果当前收益率小于或等于-1%，则卖出股票。
    """
    global positions  # 声明使用全局变量positions
    for pos in positions:
        stock_code = pos.stock_code
        volume = pos.can_use_volume
        avg_price = pos.avg_price

        if stock_code in datas:
            last_price = datas[stock_code]['lastPrice']
            profit_rate = (last_price - avg_price) / avg_price

            if profit_rate <= -0.01:
                sell_stock(stock_code, volume, 0, "止损策略", "收益率为-1%")  # 卖出可用数量


def stop_loss_max_profit(datas):
    """
    最大盈利超过0.5%且回撤幅度达到50%时的止损策略。
    """
    global positions  # 声明使用全局变量positions
    global max_profit  # 声明使用全局变量max_profit

    for pos in positions:
        stock_code = pos.stock_code
        volume = pos.can_use_volume
        avg_price = pos.avg_price

        if stock_code in datas:
            last_price = datas[stock_code]['lastPrice']

            # 初始化最大盈利率
            if stock_code not in max_profit:
                max_profit[stock_code] = (last_price - avg_price) / avg_price

            current_profit = (last_price - avg_price) / avg_price
            max_profit[stock_code] = max(max_profit[stock_code], current_profit)

            # 判断回撤止损条件
            if max_profit[stock_code] > 0.005 and current_profit <= max_profit[stock_code] * 0.5:
                sell_stock(stock_code, volume, 0, "止盈回撤策略", f"最大盈利超过0.5%，当前回撤至{current_profit}")


def stop_loss_large_profit(datas):
    """
    最大盈利超过20%且盈利回撤10个百分点时的止损策略。
    """
    global positions  # 声明使用全局变量positions
    global max_profit  # 声明使用全局变量max_profit

    for pos in positions:
        stock_code = pos.stock_code
        volume = pos.can_use_volume
        avg_price = pos.avg_price

        if stock_code in datas:
            last_price = datas[stock_code]['lastPrice']

            # 初始化最大盈利率
            if stock_code not in max_profit:
                max_profit[stock_code] = (last_price - avg_price) / avg_price

            current_profit = (last_price - avg_price) / avg_price
            max_profit[stock_code] = max(max_profit[stock_code], current_profit)

            # 判断回撤止损条件
            if max_profit[stock_code] > 0.20 and current_profit <= max_profit[stock_code] - 0.10:
                sell_stock(stock_code, volume, 0, "高盈利回撤策略", f"最大盈利超过20%，当前回撤至{current_profit}")


def call_back_functions(data):
    """
    数据回调函数，每次数据更新时调用，用于执行止损逻辑。
    """
    global positions  # 声明使用全局变量positions
    global last_update_time  # 声明使用全局变量last_update_time
    current_time = time.time()

    # 如果离上次更新小于10分钟，就不执行更新
    if current_time - last_update_time >= 600:
        positions = xt_trader.query_stock_positions(acc)  # 查询最新持仓信息
        logger.info("更新持仓。")
        last_update_time = current_time  # 更新上次更新时间

    abs_stop_loss(data)  # 执行绝对止损策略
    stop_loss_max_profit(data)  # 执行最大盈利回撤止损策略
    stop_loss_large_profit(data)  # 执行高盈利回撤止损策略


def get_stock_list_from_csv(file_path):
    """
    从CSV文件中读取股票代码列表
    """
    stock_list = []
    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row['STATUS'] == 'True':
                stock_list.append(row['SECURE'])
    return stock_list


if __name__ == '__main__':
    positions = xt_trader.query_stock_positions(acc)  # 初始化positions
    stock_list = get_stock_list_from_csv('./assets/investment_targets/investment_targets.csv')  # 从CSV文件读取股票列表
    xtdata.subscribe_whole_quote(stock_list, callback=call_back_functions)  # 订阅股票数据并设置回调函数
    xtdata.run()  # 启动数据接收和回调处理