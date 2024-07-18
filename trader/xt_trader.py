from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant import xtconstant
from pathlib2 import Path
from dotenv import load_dotenv
import os
import time
import logging  # 添加日志库
# 自定义包
from loggers import logger
from config import config
from trader.utils import generate_session_id
from trader.xt_trader_callback import MyXtQuantTraderCallback
from mini_xtclient.mini_xt import ProgramMonitor
from trader.xt_acc import acc

load_dotenv()

def setup_xt_trader():

    callback = MyXtQuantTraderCallback()

    path = Path(config['xt_client']['program_dir']).parent.parent / 'userdata_mini/'
    session_id = generate_session_id()

    xt_trader = XtQuantTrader(str(path), session_id)
    xt_trader.register_callback(callback)
    xt_trader.start()

    # 尝试连接交易服务器
    connect_result = xt_trader.connect()
    if connect_result < 0:
        app = ProgramMonitor()
        app.restart_program()
        time.sleep(15)
        connect_result = xt_trader.connect()
        if connect_result < 0:
            raise RuntimeError('Failed to connect to XT')

    # xt_trader.subscribe(acc)
    return xt_trader


xt_trader = setup_xt_trader()
subscribe_result = xt_trader.subscribe(acc)
if subscribe_result < 0:
    raise RuntimeError(f'xt_trader订阅账户【{acc.account_id}】失败。')


if __name__ == '__main__':

    try:
        xt_trader = setup_xt_trader()
    except Exception as e:
        logger.critical("Critical error in main: ", exc_info=e)
    xt_trader.subscribe(acc)

    positions = xt_trader.query_stock_positions(acc)


    for stock in positions:
        logger.info(f"证券代码:{stock.stock_code};持仓数量:{stock.volume}; 可用数量:{stock.can_use_volume}; 冻结数量:{stock.frozen_volume}; 成本价格：:{stock.avg_price}")





    print("positions:", len(positions))
    if len(positions) != 0:
        print("last position:")
        print("{0} {1} {2}".format(positions[-1].account_id, positions[-1].stock_code, positions[-1].volume))

    stock_code = '600000.SH'
    # 使用指定价下单，接口返回订单编号，后续可以用于撤单操作以及查询委托状态
    print("order using the fix price:")
    fix_result_order_id = xt_trader.order_stock(acc, stock_code, xtconstant.STOCK_BUY, 200, xtconstant.FIX_PRICE, 10.5,
                                                'strategy_name', 'remark')
    print(fix_result_order_id)
    # 使用订单编号撤单
    print("cancel order:")
    cancel_order_result = xt_trader.cancel_order_stock(acc, fix_result_order_id)
    print(cancel_order_result)