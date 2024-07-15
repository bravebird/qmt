from xtquant import xtdata

xtdata.download_history_data2(
    stock_list=['600519.SH'],
    period='1d'
)
res = xtdata.get_market_data(
    stock_list=['600519.SH'],
    period='1d'
)


if __name__ == '__main__':
    print(res)