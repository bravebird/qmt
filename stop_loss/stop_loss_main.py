import pickle  # 用于序列化和反序列化Python对象
import time  # 用于获取当前时间
from multiprocessing import Manager
from trader import xt_trader, acc, setup_xt_trader
from xtquant import xtconstant
from xtquant import xtdata
from pathlib2 import Path
from datetime import datetime
# 自定义模块
from loggers import logger  # 日志记录器
from utils.utils_data import get_targets_list_from_csv, identify_security_type
from utils.utils_xtclient import start_xt_client
from utils.utils_general import is_trading_day, is_transaction_hour

# 初始化全局变量
max_profit = {}
positions = []
max_profit_path = str(Path(__file__).parent.parent / 'assets/runtime/max_profit.pkl')


def save_max_profit(max_profit_file=max_profit_path):
    """
    保存最大收益率字典到Pickle文件
    """
    global max_profit
    global positions

    # 创建一个副本来保存需要删除的股票代码
    positions = xt_trader.query_stock_positions(acc)  # 查询最新持仓信息
    # 只保留可用股票余额大于0的持仓
    positions = [pos for pos in positions if pos.can_use_volume > 0]

    position_code_list = [pos.stock_code for pos in positions]

    stocks_to_remove = []

    # 检查每只股票的持仓量，如果持仓量为 0，最大值重置为0

    for pos in max_profit.keys():
        if pos not in position_code_list:
            max_profit[pos] = 0

        # 保存更新后的 max_profit 字典到 Pickle 文件
    try:
        with open(max_profit_file, 'wb') as f:
            pickle.dump(max_profit, f)
        logger.info(f"Max profit saved successfully to {max_profit_file}")
    except Exception as e:
        logger.error(f"Error saving max profit to Pickle file: {e}")
    logger.info(f"更新最大盈利：{max_profit}")
    return max_profit


def load_max_profit(max_profit_file=max_profit_path):
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
    return max_profit


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
    logger.trader(f'卖出股票【{stock_code}】，数量【{quantity}】，返回值为【 {response}】')
    # 更新持仓信息
    positions = xt_trader.query_stock_positions(acc)


def abs_stop_loss(datas):
    """
    绝对止损策略函数。如果当前收益率小于或等于阈值，则卖出股票。

    :param datas: 包含股票数据的字典，包含 lastPrice 信息。
    """
    global positions  # 声明使用全局变量 positions

    for pos in positions:
        stock_code = pos.stock_code
        volume = pos.can_use_volume
        avg_price = pos.avg_price

        if stock_code in datas:
            stock_type = identify_security_type(stock_code)
            if stock_type == "ETF":
                threshold = -0.005
            elif stock_type == "普通股票":
                threshold = -0.01
            else:
                logger.error(f"未知股票类型：{stock_code}")

            last_price = datas[stock_code]['lastPrice']
            if avg_price != 0:
                profit_rate = (last_price - avg_price) / avg_price

                if profit_rate <= threshold:
                    sell_stock(stock_code, volume, 0, "止损策略", f"收益率为{threshold:.2%}")  # 卖出可用数量
                    logger.warning(f"-- {datetime.now()} 股票：{stock_code}， 当前盈利：{profit_rate:.2%}")


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

        # 价格为0
        if avg_price <= 0:
            return "买入均价为0"

        if stock_code in datas.keys():
            last_price = datas[stock_code]['lastPrice']

            # 初始化最大盈利率
            if stock_code not in max_profit:
                max_profit[stock_code] = 0
                # return False

            current_profit = (last_price - avg_price) / avg_price
            if max_profit[stock_code] < current_profit:
                max_profit[stock_code] = current_profit
                save_max_profit()

            print(f"-- {datetime.now()} 股票：{stock_code}， 当前盈利：{current_profit:.2%}， 最大盈利：{max_profit[stock_code]:.2%}")

            # 判断回撤止损条件
            if max_profit[stock_code] > 0.008 and current_profit <= max_profit[stock_code] * 0.6:
                sell_stock(stock_code, volume, 0, "止盈策略", f"最大盈利超过0.8%，当前回撤至{current_profit}")
                logger.warning(f"-- {datetime.now()} 股票：{stock_code}， 当前盈利：{current_profit:.2%}， 最大盈利：{max_profit[stock_code]:.2%}")
            elif max_profit[stock_code] > 0.004 and current_profit <= 0.001:
                sell_stock(stock_code, volume, 0, "止盈策略", f"最大盈利超过0.4%，当前回撤至{current_profit}")
                logger.warning(f"-- {datetime.now()} 股票：{stock_code}， 当前盈利：{current_profit:.2%}， 最大盈利：{max_profit[stock_code]:.2%}")
        else:
            # logger.debug(f"股票价格未订阅{stock_code}
            return "未订阅股票"


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
                    max_profit[stock_code] = 0

                current_profit = (last_price - avg_price) / avg_price
                if max_profit[stock_code] < current_profit:
                    max_profit[stock_code] = current_profit
                    save_max_profit()

                # 判断回撤止损条件
                if max_profit[stock_code] > 0.35 and current_profit <= max_profit[stock_code] - 0.15:
                    sell_stock(stock_code, volume, 0, "止盈策略", f"最大盈利超过30%，当前回撤至{current_profit}")
                    logger.warning(f"-- {datetime.now()} 股票：{stock_code}， 当前盈利：{current_profit:.2%}， 最大盈利：{max_profit[stock_code]:.2%}")


def call_back_functions(data, last_update_time):
    """
    数据回调函数，每次数据更新时调用，用于执行止损逻辑。
    """

    if not is_transaction_hour():
        # logger.info("不在交易时间内")
        return False
    # logger.info(data.keys())

    global positions  # 声明使用全局变量 positions
    # positions = xt_trader.query_stock_positions(acc)
    current_time = time.time()

    # 如果离上次更新小于10分钟，就不执行更新
    if current_time - last_update_time.value >= 600:
        logger.info("止损程序监控中……")
        load_max_profit()
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

        save_max_profit()

        last_update_time.value = time.time()  # 更新上次更新时间

    abs_stop_loss(data)  # 执行绝对止损策略
    stop_loss_max_profit(data)  # 执行最大盈利回撤止损策略
    stop_loss_large_profit(data)  # 执行高盈利回撤止损策略


def stop_loss_main():
    global positions

    if not is_trading_day():
        logger.info("今天不是交易日")
        return False

    positions = xt_trader.query_stock_positions(acc)  # 查询最新持仓信息
    # 只保留可用股票余额大于0的持仓
    positions = [pos for pos in positions if pos.can_use_volume > 0]

    manager = Manager()
    last_update_time = manager.Value('d', time.time())  # 使用Manager创建共享变量
    load_max_profit()  # 加载最大收益率
    # save_max_profit()
    stock_list = get_targets_list_from_csv()  #
    logger.info(f"订阅行情{stock_list}")
    # logger.info(stock_list)
    subscribe_result = xt_trader.subscribe(acc)
    xtdata.subscribe_whole_quote(
        stock_list,
        callback=lambda data: call_back_functions(data, last_update_time)
    )  # 订阅股票数据并设置回调函数
    logger.info("止损程序启动")
    xtdata.run()

    connect_result = xt_trader.connect()
    logger.info('建立交易连接，返回0表示连接成功', connect_result)
    # 对交易回调进行订阅，订阅后可以收到交易主推，返回0表示订阅成功
    subscribe_result = xt_trader.subscribe(acc)
    logger.info('对交易回调进行订阅，订阅后可以收到交易主推，返回0表示订阅成功', subscribe_result)

    # 这一行是注册全推回调函数 包括下单判断 安全起见处于注释状态 确认理解效果后再放开
    # xtdata.subscribe_whole_quote(["SH", "SZ"], callback=f)
    # 阻塞主线程退出
    xt_trader.run_forever()


if __name__ == '__main__':

    while True:
        try:
            logger.debug('运行xtdata订阅服务。')
            stop_loss_main()
        except Exception as e:
            logger.warning("重启mini迅投客户端。")
            logger.error(e)
            start_xt_client()
        finally:
            logger.debug("finally-已经重启客户端，等待三秒。")
            time.sleep(3)
            continue
