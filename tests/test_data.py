

def test_get_training_data():
    from deep_learning.tsmixer import get_training_data
    get_training_data()


def test_subscribt_data():
    from utils.utils_data import subscribe_real_data
    subscribe_real_data()


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
