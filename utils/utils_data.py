import csv
from pathlib2 import Path
from config import config
from loggers import logger


def get_targets_list_from_csv():
    """
    从csv文件中读取股票代码列表
    """
    csv_file_path = str(Path(config['data']['investment_targets']))
    stock_list = []
    try:
        with open(csv_file_path, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['STATUS'] == 'True':
                    stock_list.append(row['SECURE'])
    except Exception as e:
        logger.error(f"Error converting CSV to Pickle: {e}")
    return stock_list
