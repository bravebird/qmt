from trader.xt_trader import ProgramMonitor
import time


def start_xt_client():
    xt_client = ProgramMonitor()
    xt_client.start_program()
    time.sleep(10)
    # xtdata.run()
    return xt_client
