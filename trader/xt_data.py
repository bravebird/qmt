from xtquant import xtdata as xt_data

if __name__ == '__main__':
    code_list = ["000001.SZ"]
    # 设定获取数据的周期
    period = "1d"

    for i in code_list:
        xt_data.download_history_data(i, period=period, incrementally=True)

    history_data = xt_data.get_market_data_ex([], code_list, period=period, count=-1)
    print(history_data)
    print("=" * 20)


    # 订阅最新行情
    def callback_func(data):
        print('回调触发', data)


    xt_data.subscribe_quote(code_list[0], period='1m', count=-1, callback=callback_func)
    print('订阅数据')
    data = xt_data.get_market_data(['close'], code_list, period='1m', start_time='20230701')
    print('一次性取数据', data)

    # 订阅全推行情
    print("*" * 20)
    def on_data(datas):
        print("打印全推数据")
        print(datas)
        # for stock_code in datas:
        #     print(stock_code, datas[stock_code])
    print("订阅全推数据")
    xt_data.subscribe_whole_quote(code_list, callback=on_data)
    print("获取全推数据")
    datas = xt_data.get_full_tick(code_list)
    print(datas)

    xt_data.run()
