import os
import json
from xtquant import xtdata
from xtquant import xtconstant
from datetime import datetime
# 自定义模块
from loggers import logger
from trader.xt_acc import acc
from trader.xt_trader import xt_trader

MAX_PROFITABILITY_FILE = 'max_profitability.json'


# 保存和加载最大收益率
def load_max_profitability():
    if os.path.exists(MAX_PROFITABILITY_FILE):
        with open(MAX_PROFITABILITY_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_max_profitability(max_profitability_data):
    with open(MAX_PROFITABILITY_FILE, 'w') as f:
        json.dump(max_profitability_data, f)


def get_current_positions():
    """
    获取当前持仓股票信息，生成股票信息字典，包括购买价格和持仓数量等
    """
    global acc
    xt_trader.subscribe(acc)
    positions = xt_trader.query_stock_positions(acc)
    return {
        position.stock_code: {
            'cost_price': position.avg_price,
            'volume': position.can_use_volume
        }
        for position in positions
    }

# =================================
def strategy_one(data, stock_code, purchase_price, volume, max_profitability):
    """
    策略1：当最大收益率大于0.5%时，如果回撤幅度超过50%则进行止损
    """
    current_price = data[-1]['close']
    current_profitability = (current_price - purchase_price) / purchase_price

    if current_profitability > max_profitability:
        max_profitability = current_profitability

    if max_profitability > 0.005:
        drawdown_percentage = (max_profitability - current_profitability) / max_profitability
        if drawdown_percentage > 0.5:
            market_type = xtconstant.MARKET_SH_CONVERT_5_CANCEL if stock_code.endswith(
                '.SH') else xtconstant.MARKET_SZ_CONVERT_5_CANCEL
            fix_result_order_id = xt_trader.order_stock(
                acc, stock_code, xtconstant.STOCK_SELL,
                volume, market_type, 0,  # 价格为0，使用市价
                '止损', '回撤幅度超过50%'
            )
            logger.info(f"Stop loss order placed for {stock_code} due to strategy one, Order ID: {fix_result_order_id}")

    return max_profitability


def strategy_two(data, stock_code, purchase_price, volume, max_profitability):
    """
    策略2：当最大收益率大于30%时，如果回撤15个百分点则进行止损
    """
    current_price = data[-1]['close']
    current_profitability = (current_price - purchase_price) / purchase_price

    if current_profitability > max_profitability:
        max_profitability = current_profitability

    if max_profitability > 0.3:
        drawdown_points = max_profitability - current_profitability
        if drawdown_points > 0.15:
            market_type = xtconstant.MARKET_SH_CONVERT_5_CANCEL if stock_code.endswith(
                '.SH') else xtconstant.MARKET_SZ_CONVERT_5_CANCEL
            fix_result_order_id = xt_trader.order_stock(
                acc, stock_code, xtconstant.STOCK_SELL,
                volume, market_type, 0,  # 价格为0，使用市价
                '止损', '回撤15个百分点'
            )
            logger.info(f"Stop loss order placed for {stock_code} due to strategy two, Order ID: {fix_result_order_id}")

    return max_profitability


def strategy_three(data, stock_code, purchase_price, volume):
    """
    策略3：当收益率为-1%时，止损
    """
    current_price = data[-1]['close']
    profitability = (current_price - purchase_price) / purchase_price

    if profitability <= -0.01:
        market_type = xtconstant.MARKET_SH_CONVERT_5_CANCEL if stock_code.endswith(
            '.SH') else xtconstant.MARKET_SZ_CONVERT_5_CANCEL
        fix_result_order_id = xt_trader.order_stock(
            acc, stock_code, xtconstant.STOCK_SELL,
            volume, market_type, 0,  # 价格为0，使用市价
            '止损', '收益率为-1%'
        )
        logger.info(f"Stop loss order placed for {stock_code} due to strategy three, Order ID: {fix_result_order_id}")
# ===============================================================


def check_stop_loss(data):
    """
    止损回调函数：调用各个策略进行止损判断
    """
    global acc, max_profitability_data

    # 动态获取当前持仓
    stock_info = get_current_positions()

    for stock_code, info in stock_info.items():
        purchase_price = info['cost_price']
        volume = info['volume']
        max_profitability = max_profitability_data.get(stock_code, 0)

        if stock_code not in data:
            continue

        # 更新最大收益率并执行策略一
        max_profitability = strategy_one(data[stock_code], stock_code, purchase_price, volume, max_profitability)

        # 更新最大收益率并执行策略二
        max_profitability = strategy_two(data[stock_code], stock_code, purchase_price, volume, max_profitability)

        # 执行策略三
        strategy_three(data[stock_code], stock_code, purchase_price, volume)

        # 更新并保存最大收益率
        max_profitability_data[stock_code] = max_profitability
        save_max_profitability(max_profitability_data)


if __name__ == "__main__":
    max_profitability_data = load_max_profitability()

    while True:
        # 动态获取当前持仓的股票代码
        my_stock_code_list = [position.stock_code for position in xt_trader.query_stock_positions(acc)]

        for stock_code in my_stock_code_list:
            xtdata.subscribe_quote(stock_code, period="1m", count=-1, callback=check_stop_loss)

        xtdata.run()  # 保持运行状态