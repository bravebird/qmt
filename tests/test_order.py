

def test_buy():
    from deep_learning.monitor_buy import buy_stock_async
    buy_stock_async(['513500.SH', '513880.SH', '159985.SZ', '159936.SZ'])


def test_get_max_price():
    # from deep_learning.monitor_buy import get_max_ask_price
    from utils.utils_data import get_max_ask_price
    for stock in ['159985.SZ', '513500.SH', '513880.SH', '159985.SZ', '159936.SZ']:
        maxprice = get_max_ask_price(stock)
        print(maxprice)

def test_trade_with_monitor():
    from deep_learning.monitor_buy import trading_with_fitted_model
    trading_with_fitted_model()
    from loggers import logger
    logger.trader("test_trade_with_monitor")
    import time
    time.sleep(20)