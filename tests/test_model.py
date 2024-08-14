import pytest
import os
from pathlib2 import Path


@pytest.fixture(scope="module", autouse=True)
def change_test_dir(request):
    """
    Fixture to change current working directory to D:/qmt at the start of the test module,
    and revert back to the original directory after tests.
    """
    original_dir = os.getcwd()
    test_dir = Path(__file__).parent.parent.as_posix()

    if not os.path.exists(test_dir):
        os.makedirs(test_dir)

    os.chdir(test_dir)

    def teardown():
        os.chdir(original_dir)

    request.addfinalizer(teardown)


def test_model_fit():
    from deep_learning.tsmixer import fit_tsmixer_model
    result = fit_tsmixer_model(test=True)
    # assert result is not None, "Model fit result should not be None"


def test_predicting():
    from deep_learning.monitor_buy import conditionally_execute_trading
    result = conditionally_execute_trading(test=True)
    # assert result is not None, "Trading result should not be None"


def test_buy_stock_async():
    from deep_learning.monitor_buy import buy_stock_async
    result = buy_stock_async(['601838.SH', '512290.SH'])
    # assert result is not None, "Stock buying result should not be None"

def test_get_tick_price():
    from utils.utils_data import get_max_ask_price
    for stock in ["159869.SZ", "588120.SH"]:
        get_max_ask_price(stock)

def test_trading_with_fitted_model():
    from deep_learning.monitor_buy import trading_with_fitted_model
    result = trading_with_fitted_model()


def test_fit_tsmixer_model():
    from deep_learning.tsmixer import fit_tsmixer_model
    fit_tsmixer_model(test=True)


if __name__ == '__main__':
    os.getcwd()
    pytest.main()