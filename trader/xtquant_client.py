# coding=utf-8
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
from xtquant import xtconstant
from pathlib2 import Path
from dotenv import load_dotenv
import os
import uuid
import time
import random

from loggers import logger
from config import config

# 加载环境变量
load_dotenv()


def generate_session_id():
    """
    生成一个基于日期和时间戳的唯一 32 位整数会话 ID，确保在同一天内不重复
    :return: 唯一的会话 ID 整数
    """
    # 获取当前日期和时间的秒级时间戳
    now = time.localtime()
    date_str = time.strftime("%Y%m%d", now)  # 格式化为 YYYYMMDD
    timestamp = int(time.mktime(now))  # 当前时间的秒级时间戳

    # 生成一个 12 位的随机数
    random_number = random.randint(0, 4095)  # 12 位的随机数范围是 0 到 4095

    # 将日期字符串转换为整数
    date_int = int(date_str)

    # 将日期整数和时间戳的最后 20 位组合成一个 32 位整数
    session_id = (date_int << 12) | random_number

    return session_id


class MyXtQuantTraderCallback(XtQuantTraderCallback):
    """回调类，用于处理交易服务器推送的各种事件"""

    def on_disconnected(self):
        """
        连接断开时的回调
        """
        logger.info("Connection lost")  # 记录连接断开信息

    def on_stock_order(self, order):
        """
        委托回报推送时处理
        :param order: XtOrder对象
        """
        logger.debug("On order callback:")
        logger.debug(
            f"Stock Code: {order.stock_code}; Order Status: {order.order_status}; Order SysID: {order.order_sysid}")

    def on_stock_asset(self, asset):
        """
        资金变动推送时处理
        :param asset: XtAsset对象
        """
        logger.debug("On asset callback")
        logger.debug(f"Account ID: {asset.account_id}; Cash: {asset.cash}; Total Asset: {asset.total_asset}")

    def on_stock_trade(self, trade):
        """
        成交变动推送时处理
        :param trade: XtTrade对象
        """
        logger.debug("On trade callback")
        logger.debug(f"Account ID: {trade.account_id}; Stock Code: {trade.stock_code}; Order ID: {trade.order_id}")

    def on_stock_position(self, position):
        """
        持仓变动推送时处理
        :param position: XtPosition对象
        """
        logger.debug("On position callback")
        logger.debug(f"Stock Code: {position.stock_code}; Volume: {position.volume}")

    def on_order_error(self, order_error):
        """
        委托失败推送时处理
        :param order_error: XtOrderError 对象
        """
        logger.debug("On order_error callback")
        logger.error(
            f"Order ID: {order_error.order_id}; Error ID: {order_error.error_id}; Error Msg: {order_error.error_msg}")

    def on_cancel_error(self, cancel_error):
        """
        撤单失败推送时处理
        :param cancel_error: XtCancelError 对象
        """
        logger.debug("On cancel_error callback")
        logger.info(
            f"Order ID: {cancel_error.order_id}; Error ID: {cancel_error.error_id}; Error Msg: {cancel_error.error_msg}")

    def on_order_stock_async_response(self, response):
        """
        异步下单回报推送时处理
        :param response: XtOrderResponse 对象
        """
        logger.debug("On_order_stock_async_response")
        logger.debug(f"Account ID: {response.account_id}; Order ID: {response.order_id}; Seq: {response.seq}")

    def on_account_status(self, status):
        """
        账户状态变更推送时处理
        :param status: XtAccountStatus 对象
        """
        logger.debug("On account status")
        logger.debug(f"Account ID: {status.account_id}; Account Type: {status.account_type}; Status: {status.status}")


if __name__ == "__main__":
    # path 为 mini qmt 客户端安装目录下的 userdata_mini 路径
    path = Path(config['xt_client'].get('program_dir')).parent.parent / "userdata_mini"
    # session_id 为会话编号，不同的Python策略需要使用不同的会话编号
    logger.warning(f"Path: {path}")

    session_id = generate_session_id()
    logger.info(f"链接的session_id: {session_id}")

    # 配置账户和股票代码
    xt_trader = XtQuantTrader(path.as_posix(), session_id)

    # 创建资金账号实例
    acc = StockAccount(os.getenv("MINI_XT_USER"))

    # 创建自定义回调类实例，并进行注册
    callback = MyXtQuantTraderCallback()
    xt_trader.register_callback(callback)

    # ----------------------
    # 启动交易线程
    xt_trader.start()

    # 建立交易连接，返回0表示连接成功
    connect_result = xt_trader.connect()
    logger.info(f"Connect Result: {connect_result}")

    # 订阅交易回调，返回0表示订阅成功
    subscribe_result = xt_trader.subscribe(acc)
    logger.info(f"Subscribe Result: {subscribe_result}")

    stock_code = '600000.SH'

    # 使用指定价下单，返回订单编号
    logger.info("Order using the fixed price:")
    fix_result_order_id = xt_trader.order_stock(
        acc,  # 资金账号
        stock_code,  # 证券代码
        xtconstant.STOCK_BUY,  # 委托类型
        200,  # 委托数量
        xtconstant.FIX_PRICE,  # 报价类型
        10.5,  # 委托价格
        'strategy_name',  # 策略名称
        'remark'  # 委托备注
    )
    logger.info(f"Fixed Price Order ID: {fix_result_order_id}")
    # 委托成功，只是成功提交。不代表报单符合要求，不代表报单已经成交。

    # 使用订单编号撤单
    logger.info("Cancel order:")
    cancel_order_result = xt_trader.cancel_order_stock(acc, fix_result_order_id)
    logger.info(f"Cancel Order Result: {cancel_order_result}")

    # 使用异步下单接口，返回下单请求序号
    logger.info("Order using async API:")
    async_seq = xt_trader.order_stock_async(
        acc,
        stock_code,
        xtconstant.STOCK_BUY,
        200,
        xtconstant.FIX_PRICE,
        10.5,
        'strategy_name',
        'remark'
    )
    logger.info(f"Async Order Seq: {async_seq}")

    # 查询证券资产
    logger.info("Query asset:")
    asset = xt_trader.query_stock_asset(acc)
    if asset:
        logger.info("Asset:")
        logger.info(f"Cash: {asset.cash}")

        # 根据订单编号查询委托
    logger.info("Query order:")
    order = xt_trader.query_stock_order(acc, fix_result_order_id)
    if order:
        logger.info("Order:")
        logger.info(f"Order ID: {order.order_id}")

        # 查询当日所有的委托
    logger.info("Query orders:")
    orders = xt_trader.query_stock_orders(acc)
    logger.info(f"Orders Count: {len(orders)}")
    if len(orders) != 0:
        logger.info("Last order:")
        logger.info(f"{orders[-1].stock_code} {orders[-1].order_volume} {orders[-1].price}")

        # 查询当日所有的成交
    logger.info("Query trades:")
    trades = xt_trader.query_stock_trades(acc)
    logger.info(f"Trades Count: {len(trades)}")
    if len(trades) != 0:
        logger.info("Last trade:")
        logger.info(f"{trades[-1].stock_code} {trades[-1].traded_volume} {trades[-1].traded_price}")

        # 查询当日所有的持仓
    logger.info("Query positions:")
    positions = xt_trader.query_stock_positions(acc)
    logger.info(f"Positions Count: {len(positions)}")
    if len(positions) != 0:
        logger.info("Last position:")
        logger.info(f"{positions[-1].account_id} {positions[-1].stock_code} {positions[-1].volume}")

        # 根据股票代码查询对应持仓
    logger.info("Query position:")
    position = xt_trader.query_stock_position(acc, stock_code)
    if position:
        logger.info("Position:")
        logger.info(f"{position.account_id} {position.stock_code} {position.volume}")

        # 阻塞线程，接收交易推送
    xt_trader.run_forever()
