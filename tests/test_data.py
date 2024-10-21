

def test_get_training_data():
    from deep_learning.tsmixer import get_training_data
    get_training_data()


# def test_subscribt_data():
#     from utils.utils_data import subscribe_real_data
#     subscribe_real_data()


def test_get_combined_timeseries():
    from data.prepare_combined_timeseries import get_combined_timeseries
    get_combined_timeseries(mode='training')
    get_combined_timeseries(mode='predicting')

    from data.prepare_multi_timeseries_list import prepare_multi_timeseries_list
    prepare_multi_timeseries_list(mode='training')
    prepare_multi_timeseries_list(mode='predicting')


def test_fetch_and_clean_data():
    from data.prepare_combined_timeseries import fetch_and_clean_data
    df = fetch_and_clean_data()


def test_get_positions():
    from trader import xt_trader, acc, setup_xt_trader
    from utils.utils_data import get_targets_list_from_csv

    positions = xt_trader.query_stock_positions(acc)
    # print([pos.incomeRate for pos in positions])
    print(dir(positions[0]))
    targets = get_targets_list_from_csv()
    print(targets)

    for pos in positions:
        if pos.stock_code in targets:
            print(pos.stock_code, pos.can_use_volume)
