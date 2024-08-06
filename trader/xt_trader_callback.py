from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
# from xtquant import xtdata
from xtquant import xtconstant
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
import os
import time
# 自定义包
from loggers import logger
from config import config
from mini_xtclient.mini_xt import ProgramMonitor
from utils.utils_general import generate_session_id
from config.data_dic import order_type_dic
# from utils.utils_xtclient import start_xt_client


class MyXtQuantTraderCallback(XtQuantTraderCallback):

    def on_disconnected(self):
        """
        连接断开
        :return:
        """
        logger.warning("连接丢失，检查客户端是否启动。")
        # 交给错误处理程序处理。
        raise Exception("行情服务连接断开")
        # return None


    def on_stock_order(self, order):
        """
        委托回报推送
        :param order: XtOrder对象
        :return:
        """
        logger.info(f"on order callback: {order.stock_code}, {order.order_status}, {order.order_sysid}")

    def on_stock_asset(self, asset):
        """
        资金变动推送
        :param asset: XtAsset对象
        :return:
        """
        logger.info(f"on asset callback: {asset.account_id}, cash: {asset.cash}, total_asset: {asset.total_asset}")

    def on_stock_trade(self, trade):
        """
        成交变动推送
        :param trade: XtTrade对象
        :return:
        """
        order_type = order_type_dic.get(trade.order_type, '未定义')
        traded_time = datetime.fromtimestamp(trade.traded_time)
        logger.trader(f"【{order_type}-{trade.strategy_name}】股票代码: {trade.stock_code}， 成交金额: {trade.traded_amount}， 成交数量: {trade.traded_volume}， 成交价格: {trade.traded_price}， 成交时间: {traded_time}， 备注：{trade.order_remark}")

    def on_stock_position(self, position):
        """
        持仓变动推送
        :param position: XtPosition对象
        :return:
        """
        logger.logger(
            f"交易回调信息【持仓变动】: 证券代码:{position.stock_code};持仓数量:{position.volume}; 可用数量:{position.can_use_volume}; 冻结数量:{position.frozen_volume}; 成本价格：:{position.avg_price}"
        )

    def on_order_error(self, order_error):
        """
        委托失败推送
        :param order_error:XtOrderError 对象
        :return:
        """
        logger.error(
            f"交易回调信息【order_error】: {order_error.order_id}, error_id: {order_error.error_id}, error_msg: {order_error.error_msg}")

    def on_cancel_error(self, cancel_error):
        """
        撤单失败推送
        :param cancel_error: XtCancelError 对象
        :return:
        """
        logger.error(
            f"交易回调信息【cancel_error】: {cancel_error.order_id}, error_id: {cancel_error.error_id}, error_msg: {cancel_error.error_msg}")

    def on_order_stock_async_response(self, response):
        """
        异步下单回报推送
        :param response: XtOrderResponse 对象
        :return:
        """
        logger.info(
            f"on_order_stock_async_response: {response.account_id}, order_id: {response.order_id}, seq: {response.seq}")

    def on_account_status(self, status):
        """
        :param status: XtAccountStatus 对象
        :return:
        """
        match status.status:
            case xtconstant.ACCOUNT_STATUS_INVALID:
                logger.info("账户无效。")
            case xtconstant.ACCOUNT_STATUS_OK:
                logger.info("账户正常。")
            case xtconstant.ACCOUNT_STATUS_WAITING_LOGIN:
                logger.info("账户连接中。")
                # xt_client = ProgramMonitor()
                # xt_client.start_program()
            case xtconstant.ACCOUNT_STATUSING:
                logger.info("账户登录中。")
            case xtconstant.ACCOUNT_STATUS_FAIL:
                logger.info("账户登录失败。")
            case xtconstant.ACCOUNT_STATUS_INITING:
                logger.info("账户初始化中。")
            case xtconstant.ACCOUNT_STATUS_CORRECTING:
                logger.info("账户数据刷新校正中。")
            case xtconstant.ACCOUNT_STATUS_CLOSED:
                logger.info("收盘后。")
            case xtconstant.ACCOUNT_STATUS_ASSIS_FAIL:
                logger.info("穿透副链接断开。")
            case xtconstant.ACCOUNT_STATUS_DISABLEBYSYS:
                logger.info("系统停用（密码错误超限）。")
            case xtconstant.ACCOUNT_STATUS_DISABLEBYUSER:
                logger.info("用户停用。")
            case _:
                logger.info("无效的账户状态。")
                logger.info(
                    f"on_account_status: {status.account_id}, account_type: {status.account_type}, status: {status.status}")


if __name__ == "__main__":
    load_dotenv()

    logger.info("demo test")

    # path为mini qmt客户端安装目录下userdata_mini路径
    path = Path(config['xt_client']['program_dir']).parent.parent / 'userdata_mini/'

    # session_id为会话编号，策略使用方对于不同的Python策略需要使用不同的会话编号
    session_id = generate_session_id()
    xt_trader = XtQuantTrader(str(path), session_id)
    acc = StockAccount(os.getenv("MINI_XT_USER"))

    callback = MyXtQuantTraderCallback()
    xt_trader.register_callback(callback)
    xt_trader.start()

    connect_result = xt_trader.connect()
    logger.info(f"Connect result: {connect_result}")

    subscribe_result = xt_trader.subscribe(acc)
    logger.info(f"Subscribe result: {subscribe_result}")

    stock_code = '600000.SH'

    # 使用指定价下单，接口返回订单编号，后续可以用于撤单操作以及查询委托状态
    logger.info("order using the fix price:")
    fix_result_order_id = xt_trader.order_stock(acc, stock_code, xtconstant.STOCK_BUY, 200, xtconstant.FIX_PRICE, 10.5,
                                                'strategy_name', 'remark')
    logger.info(f"Fix result order ID: {fix_result_order_id}")

    # 使用订单编号撤单
    logger.info("cancel order:")
    cancel_order_result = xt_trader.cancel_order_stock(acc, fix_result_order_id)
    logger.info(f"Cancel order result: {cancel_order_result}")

    # 使用异步下单接口，接口返回下单请求序号seq，seq可以和on_order_stock_async_response的委托反馈response对应起来
    logger.info("order using async api:")
    async_seq = xt_trader.order_stock_async(acc, stock_code, xtconstant.STOCK_BUY, 200, xtconstant.FIX_PRICE, 10.5,
                                            'strategy_name', 'remark')
    logger.info(f"Async seq: {async_seq}")

    # 查询证券资产
    logger.info("query asset:")
    asset = xt_trader.query_stock_asset(acc)
    if asset:
        logger.info(f"Asset cash: {asset.cash}")

        # 根据订单编号查询委托
    logger.info("query order:")
    order = xt_trader.query_stock_order(acc, fix_result_order_id)
    if order:
        logger.info(f"Order ID: {order.order_id}")

        # 查询当日所有的委托
    logger.info("query orders:")
    orders = xt_trader.query_stock_orders(acc)
    logger.info(f"Orders count: {len(orders)}")
    if orders:
        last_order = orders[-1]
        logger.info(
            f"Last order - stock_code: {last_order.stock_code}, order_volume: {last_order.order_volume}, price: {last_order.price}")

        # 查询当日所有的成交
    logger.info("query trade:")
    trades = xt_trader.query_stock_trades(acc)
    logger.info(f"Trades count: {len(trades)}")
    if trades:
        last_trade = trades[-1]
        logger.info(
            f"Last trade - stock_code: {last_trade.stock_code}, traded_volume: {last_trade.traded_volume}, traded_price: {last_trade.traded_price}")

        # 查询当日所有的持仓
    logger.info("query positions:")
    positions = xt_trader.query_stock_positions(acc)
    logger.info(f"Positions count: {len(positions)}")
    if positions:
        last_position = positions[-1]
        logger.info(
            f"Last position - account_id: {last_position.account_id}, stock_code: {last_position.stock_code}, volume: {last_position.volume}")

        # 根据股票代码查询对应持仓
    logger.info("query position:")
    position = xt_trader.query_stock_position(acc, stock_code)
    if position:
        logger.info(
            f"Position - account_id: {position.account_id}, stock_code: {position.stock_code}, volume: {position.volume}")

        # 阻塞线程，接收交易推送
    xt_trader.run_forever()


