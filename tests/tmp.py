import csv  # 用于读取CSV文件
import pickle  # 用于序列化和反序列化Python对象
import time  # 用于获取当前时间
from trader import xt_trader, acc
from xtquant import xtconstant
from xtquant import xtdata
from loggers import logger

# 定义文件路径
MAX_PROFIT_FILE = 'assets/max_profit.pkl'
STOCK_LIST_CSV_FILE = './assets/investment_targets/investment_targets.csv'
STOCK_LIST_PKL_FILE = './assets/investment_targets/investment_targets.pkl'

# 初始化全局变量
max_profit = {}
positions = []
last_update_time = time.time()  # 初始化为当前时间


def save_max_profit():
    """
    保存最大收益率字典到Pickle文件
    """
    global max_profit
    global positions
    global last_update_time  # 再次声明全局变量

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
        with open(MAX_PROFIT_FILE, 'wb') as f:
            pickle.dump(max_profit, f)
        logger.info(f"Max profit saved successfully to {MAX_PROFIT_FILE}")
    except Exception as e:
        logger.error(f"Error saving max profit to Pickle file: {e}")


def load_max_profit():
    """
    从Pickle文件加载最大收益率字典
    """
    global max_profit
    global last_update_time  # 再次声明全局变量

    try:
        with open(MAX_PROFIT_FILE, 'rb') as f:
            max_profit = pickle.load(f)
        logger.info(f"Max profit loaded successfully from {MAX_PROFIT_FILE}")
    except FileNotFoundError:
        max_profit = {}
        logger.warning(f"Max profit file not found: {MAX_PROFIT_FILE}. Starting with an empty dictionary.")
    except Exception as e:
        logger.error(f"Error loading max profit from Pickle file: {e}")
        max_profit = {}


def sell_stock(stock_code, quantity, price=0, strategy_name='', order_remark=''):
    """
    卖出股票函数，根据股票代码后缀确定所属市场并设置order_type后，异步发出卖出指令。
    """
    global last_update_time  # 再次声明全局变量

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


def abs_stop_loss(datas):
    """
    绝对止损策略函数，如果当前收益率小于或等于-1%，则卖出股票。
    """
    global positions  # 声明使用全局变量 positions
    global last_update_time  # 再次声明全局变量

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
    global last_update_time  # 再次声明全局变量

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
                max_profit[stock_code] = max(max_profit[stock_code], current_profit)

                # 判断回撤止损条件
                if max_profit[stock_code] > 0.005 and current_profit <= max_profit[stock_code] * 0.5:
                    sell_stock(stock_code, volume, 0, "止盈回撤策略", f"最大盈利超过0.5%，当前回撤至{current_profit}")


def stop_loss_large_profit(datas):
    """
    最大盈利超过20%且盈利回撤10个百分点时的止损策略。
    """
    global positions  # 声明使用全局变量 positions
    global max_profit  # 声明使用全局变量 max_profit
    global last_update_time  # 再次声明全局变量

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
                max_profit[stock_code] = max(max_profit[stock_code], current_profit)
                # logger.info(f"{stock_code}-{avg_price}-{max_profit}-{current_profit}")

                # 判断回撤止损条件
                if max_profit[stock_code] > 0.20 and current_profit <= max_profit[stock_code] - 0.10:
                    sell_stock(stock_code, volume, 0, "高盈利回撤策略", f"最大盈利超过20%，当前回撤至{current_profit}")


def call_back_functions(data):
    """
    数据回调函数，每次数据更新时调用，用于执行止损逻辑。
    """
    global positions  # 声明使用全局变量 positions
    global last_update_time  # 声明使用全局变量 last_update_time
    current_time = time.time()

    # 调试信息：输出回调数据
    logger.info(f"Received callback data: {data}")

    # 如果离上次更新小于10分钟，就不执行更新
    if current_time - last_update_time >= 600:
        positions = xt_trader.query_stock_positions(acc)  # 查询最新持仓信息
        # 只保留可用股票余额大于0的持仓
        positions = [pos for pos in positions if pos.can_use_volume > 0]
        logger.info("更新持仓。")

        # 撤销未成交的订单
        pending_orders = xt_trader.query_stock_orders(acc)
        for order in pending_orders:
            cancel_response = xt_trader.cancel_order(acc, order.order_id)
            logger.info(f"撤销订单 {order.order_id}。Response: {cancel_response}")

        last_update_time = current_time  # 更新上次更新时间

    abs_stop_loss(data)  # 执行绝对止损策略
    stop_loss_max_profit(data)  # 执行最大盈利回撤止损策略
    stop_loss_large_profit(data)  # 执行高盈利回撤止损策略

    save_max_profit()  # 保存最大收益率


def csv_to_pkl(csv_file_path, pkl_file_path):
    """
    将CSV文件转换为Pickle文件
    """
    stock_list = []
    try:
        with open(csv_file_path, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['STATUS'] == 'True':
                    stock_list.append(row['SECURE'])
        with open(pkl_file_path, 'wb') as file:
            pickle.dump(stock_list, file)
        logger.info(f"Converted {csv_file_path} to {pkl_file_path}")
    except Exception as e:
        logger.error(f"Error converting CSV to Pickle: {e}")


def get_stock_list_from_pkl(file_path):
    """
    从Pickle文件中读取股票代码列表
    """
    stock_list = []
    try:
        with open(file_path, 'rb') as file:
            stock_list = pickle.load(file)
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
    except Exception as e:
        logger.error(f"Error reading stock list from Pickle file: {e}")
    return stock_list


if __name__ == '__main__':
    load_max_profit()  # 加载最大收益率
    csv_to_pkl(STOCK_LIST_CSV_FILE, STOCK_LIST_PKL_FILE)  # 将CSV文件转换为Pickle文件
    positions = xt_trader.query_stock_positions(acc)  # 初始化positions
    stock_list = get_stock_list_from_pkl(STOCK_LIST_PKL_FILE)  # 从Pickle文件读取股票列表
    xtdata.subscribe_whole_quote(stock_list, callback=call_back_functions)  # 订阅股票数据并设置回调函数
    xtdata.run()  # 启动数据接收和回调处理