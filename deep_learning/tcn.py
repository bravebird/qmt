import xtquant.xtdata as xtdata
import pandas as pd
import numpy as np
from darts import TimeSeries
from darts.models import TCNModel
from darts.metrics import mape
import matplotlib.pyplot as plt
import logging
from datetime import datetime, timedelta
from matplotlib import font_manager as fm

# Settings for logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load font
font_path = 'assets/sider-font/微软雅黑.ttf'
font_prop = fm.FontProperties(fname=font_path)

# Step 1: Download data
def download_data(stock_code, start_date, end_date):
    try:
        xtdata.download_history_data(
            stock_code,
            period='1d',
            start_time=start_date,
            end_time=end_date
        )
        logger.info(f"Successfully downloaded data for {stock_code}")
    except Exception as e:
        logger.error(f"Error downloading data for {stock_code}: {e}")

# Step 2: Fetch data via xtquant
def get_stock_data(stock_code, start_date, end_date):
    try:
        data = xtdata.get_local_data(
            stock_list=[stock_code],
            period='1d',
            start_time=start_date,
            end_time=end_date,
            count=-1,
            dividend_type='none',
            fill_data=True
        )
        df = pd.DataFrame(data[stock_code])
        df['time'] = range(len(df))
        logger.info(f"Successfully retrieved data for {stock_code}")
        return df
    except Exception as e:
        logger.error(f"Error retrieving data for {stock_code}: {e}")
        return None

# Step 3: Preprocess data
def preprocess_data(df):
    df['next_day_open'] = df['open'].shift(-1)
    df['price_change'] = (df['next_day_open'] - df['close']) / df['close']
    df.dropna(inplace=True)
    return df

# Step 4: Train and predict using TCNModel
def train_and_predict(data, train_ratio=0.8):
    series = TimeSeries.from_dataframe(data, 'time', 'price_change')
    train, test = series.split_before(train_ratio)

    model = TCNModel(
        input_chunk_length=30,
        output_chunk_length=1,
        n_epochs=100,
        random_state=42
    )

    model.fit(train)
    predictions = model.predict(len(test))

    return train, test, predictions

# Step 5: Evaluate and visualize
def evaluate_and_visualize(train, test, predictions):
    plt.figure(figsize=(10, 6))
    train.plot(label='Train')
    test.plot(label='Test')
    predictions.plot(label='Forecast')
    plt.legend(prop=font_prop)
    plt.title('Stock Price Change Prediction', fontproperties=font_prop)
    plt.show()

    # Ensure actual values are strictly positive
    positive_test_values = np.array(test.values())
    positive_mask = positive_test_values > 0

    positive_test = TimeSeries.from_times_and_values(
        test.time_index[positive_mask],
        test.values()[positive_mask]
    )

    positive_predictions = predictions.slice_intersect(positive_test)

    if len(positive_test) > 0:
        error = mape(positive_test, positive_predictions)
        logger.info(f"Mean Absolute Percentage Error: {error:.2f}%")
    else:
        logger.warning("No strictly positive values for MAPE calculation")

    # Print some stats
    logger.info(f"Train set size: {len(train)}")
    logger.info(f"Test set size: {len(test)}")
    logger.info(f"Prediction set size: {len(predictions)}")
    logger.info(f"Positive test set size: {len(positive_test)}")

# Main function
def main():
    stock_code = '601318.SH'  # Example stock code
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=365 * 3)).strftime('%Y%m%d')  # 3 years of data

    # Download data
    download_data(stock_code, start_date, end_date)

    # Fetch data
    df = get_stock_data(stock_code, start_date, end_date)
    if df is None:
        return

    # Preprocess
    df = preprocess_data(df)

    # Train and predict
    train, test, predictions = train_and_predict(df)

    # Evaluate and visualize
    evaluate_and_visualize(train, test, predictions)

if __name__ == '__main__':
    main()