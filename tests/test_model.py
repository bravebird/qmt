
def test_model_fit():
    from deep_learning.tsmixer import fit_tsmixer_model
    fit_tsmixer_model(test=True)


def test_predicting():
    from deep_learning.monitor_buy import conditionally_execute_trading
    conditionally_execute_trading(test=True)

def test_buy_stock_async():
    from deep_learning.monitor_buy import buy_stock_async
    buy_stock_async(['601838.SH'])