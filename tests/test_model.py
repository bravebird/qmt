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
    result = buy_stock_async(['601838.SH'])
    # assert result is not None, "Stock buying result should not be None"


if __name__ == '__main__':
    os.getcwd()
    pytest.main()