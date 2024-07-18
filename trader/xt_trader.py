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


try:
    xt_trader = setup_xt_trader()
except Exception as e:
    logger.critical("Critical error in main: ", exc_info=e)
xt_trader.subscribe(acc)

if __name__ == '__main__':
    logger.info("启动xt_trader.run_forever")
    xt_trader.run_forever()
