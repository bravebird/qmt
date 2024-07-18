import os
import json
from datetime import datetime
from xtquant import xtdata, xttrader, xtconstant
from xtquant.xttrader import XtQuantTraderCallback
# 自定义模块
from loggers import logger
from trader.xt_acc import acc  # 假设这个模块定义了交易账号
from trader.xt_trader import xt_trader  # 假设这个模块定义了交易功能

MAX_PROFITABILITY_FILE = 'max_profitability.json'
STOCK_INFO_FILE = 'stock_info.json'


class StockInfo:
    """
    存储单只股票的持仓信息，包括股票代码、购买价格、持仓数量、最大收益率和时间戳。
    """

    def __init__(self, stock_code, purchase_price, volume, max_profitability=0, timestamp=None):
        self.stock_code = stock_code
        self.purchase_price = purchase_price
        self.volume = volume
        self.max_profitability = max_profitability
        self.timestamp = timestamp or datetime.now().isoformat()

    def update_max_profitability(self, new_profitability):
        """
        更新最大收益率，如果新的收益率大于当前的最大收益率。
        """
        if new_profitability > self.max_profitability:
            self.max_profitability = new_profitability

    def to_dict(self):
        """
        将对象转换为字典格式。
        """
        return {
            'stock_code': self.stock_code,
            'purchase_price': self.purchase_price,
            'volume': self.volume,
            'max_profitability': self.max_profitability,
            'timestamp': self.timestamp
        }

    @staticmethod
    def from_dict(data):
        """
        从字典格式创建对象。
        """
        return StockInfo(
            stock_code=data['stock_code'],
            purchase_price=data['purchase_price'],
            volume=data['volume'],
            max_profitability=data.get('max_profitability', 0),
            timestamp=data.get('timestamp')
        )


def load_stock_info():
    """
    从文件加载股票信息数据。
    """
    if os.path.exists(STOCK_INFO_FILE):
        with open(STOCK_INFO_FILE, 'r') as f:
            data = json.load(f)
            return {k: StockInfo.from_dict(v) for k, v in data.items()}
    return {}


def save_stock_info(stock_info_dict):
    """
    将股票信息数据保存到文件。
    """
    data = {k: v.to_dict() for k, v in stock_info_dict.items()}
    with open(STOCK_INFO_FILE, 'w') as f:
        json.dump(data, f)


def load_max_profitability():
    """
    从文件加载最大收益率数据。
    """
    if os.path.exists(MAX_PROFITABILITY_FILE):
        with open(MAX_PROFITABILITY_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_max_profitability(max_profitability_data):
    """
    将最大收益率数据保存到文件。
    """
    with open(MAX_PROFITABILITY_FILE, 'w') as f:
        json.dump(max_profitability_data, f)


def get_current_positions():
    """
    获取当前的持仓信息，并生成包含股票代码、购买价格、持仓数量等信息的字典。
    """
    global acc
    xt_trader.subscribe(acc)
    positions = xt_trader.query_stock_positions(acc)
    return {
        position.stock_code: StockInfo(position.stock_code, position.avg_price, position.can_use_volume)
        for position in positions
    }


class TraderCallback(XtQuantTraderCallback):
    """
    持仓变动回调函数。
    """

    def __init__(self, stock_info_dict):
        super(TraderCallback, self).__init__()
        self.stock_info_dict = stock_info_dict

    def on_stock_position(self, position):
        stock_code = position.stock_code
        if position.can_use_volume > 0:
            self.stock_info_dict[stock_code] = StockInfo(
                stock_code,
                position.avg_price,
                position.can_use_volume
            )
        else:
            if stock_code in self.stock_info_dict:
                del self.stock_info_dict[stock_code]

        logger.info("Position info updated.")
        update_quotes_subscription(self.stock_info_dict)


def strategy_one(stock_info, data):
    """
    策略1：当最大收益率大于0.5%时，如果回撤幅度超过50%则进行止损。
    """
    current_price = data[-1]['close']
    current_profitability = (current_price - stock_info.purchase_price) / stock_info.purchase_price

    stock_info.update_max_profitability(current_profitability)

    if stock_info.max_profitability > 0.005:
        drawdown_percentage = (stock_info.max_profitability - current_profitability) / stock_info.max_profitability
        if drawdown_percentage > 0.5:
            market_type = xtconstant.MARKET_SH_CONVERT_5_CANCEL if stock_info.stock_code.endswith(
                '.SH') else xtconstant.MARKET_SZ_CONVERT_5_CANCEL
            fix_result_order_id = xt_trader.order_stock(
                acc, stock_info.stock_code, xtconstant.STOCK_SELL,
                stock_info.volume, market_type, 0,  # 价格为0，使用市价
                '止损', '回撤幅度超过50%'
            )
            logger.info(
                f"Stop loss order placed for {stock_info.stock_code} due to strategy one, Order ID: {fix_result_order_id}")
            stock_info.timestamp = datetime.now().isoformat()
    return stock_info.max_profitability


def strategy_two(stock_info, data):
    """
    策略2：当最大收益率大于30%时，如果回撤15个百分点则进行止损。
    """
    current_price = data[-1]['close']
    current_profitability = (current_price - stock_info.purchase_price) / stock_info.purchase_price

    stock_info.update_max_profitability(current_profitability)

    if stock_info.max_profitability > 0.3:
        drawdown_points = stock_info.max_profitability - current_profitability
        if drawdown_points > 0.15:
            market_type = xtconstant.MARKET_SH_CONVERT_5_CANCEL if stock_info.stock_code.endswith(
                '.SH') else xtconstant.MARKET_SZ_CONVERT_5_CANCEL
            fix_result_order_id = xt_trader.order_stock(
                acc, stock_info.stock_code, xtconstant.STOCK_SELL,
                stock_info.volume, market_type, 0,  # 价格为0，使用市价
                '止损', '回撤15个百分点'
            )
            logger.info(
                f"Stop loss order placed for {stock_info.stock_code} due to strategy two, Order ID: {fix_result_order_id}")
            stock_info.timestamp = datetime.now().isoformat()
    return stock_info.max_profitability


def strategy_three(stock_info, data):
    """
    策略3：当收益率为-1%时，止损。
    """
    current_price = data[-1]['close']
    profitability = (current_price - stock_info.purchase_price) / stock_info.purchase_price

    if profitability <= -0.01:
        market_type = xtconstant.MARKET_SH_CONVERT_5_CANCEL if stock_info.stock_code.endswith(
            '.SH') else xtconstant.MARKET_SZ_CONVERT_5_CANCEL
        fix_result_order_id = xt_trader.order_stock(
            acc, stock_info.stock_code, xtconstant.STOCK_SELL,
            stock_info.volume, market_type, 0,  # 价格为0，使用市价
            '止损', '收益率为-1%'
        )
        logger.info(
            f"Stop loss order placed for {stock_info.stock_code} due to strategy three, Order ID: {fix_result_order_id}")
        stock_info.timestamp = datetime.now().isoformat()
    return stock_info.max_profitability


def on_market_data_update(data, stock_info_dict, max_profitability_data):
    """
    市场数据更新事件处理函数，当新的市场数据到来时，检查止损条件。
    """
    stock_code = data[-1]['code']
    if stock_code in stock_info_dict:
        stock_info = stock_info_dict[stock_code]

        # 调用各个策略
        max_profitability_data[stock_code] = strategy_one(stock_info, data)
        max_profitability_data[stock_code] = strategy_two(stock_info, data)
        max_profitability_data[stock_code] = strategy_three(stock_info, data)

        # 保存最大收益率数据和股票信息
        save_max_profitability(max_profitability_data)
        save_stock_info(stock_info_dict)


def update_quotes_subscription(stock_info_dict):
    """
    根据当前持仓更新订阅的股票数据。
    """
    for stock_code in stock_info_dict.keys():
        xtdata.subscribe_quote(stock_code, period="1m", count=-1,
                               callback=lambda data: on_market_data_update(data, stock_info_dict,
                                                                           max_profitability_data))
    logger.info("Market data subscription updated.")


if __name__ == "__main__":
    stock_info_dict = load_stock_info()  # 加载股票信息数据
    max_profitability_data = load_max_profitability()  # 加载最大收益率数据

    # 获取当前持仓信息并更新
    current_positions = get_current_positions()
    for stock_code, stock_info in current_positions.items():
        if stock_code in stock_info_dict:
            stock_info_dict[stock_code].volume = stock_info.volume
            stock_info_dict[stock_code].purchase_price = stock_info.purchase_price
        else:
            stock_info_dict[stock_code] = stock_info

            # 移除持仓数为0的股票信息
    stock_info_dict = {k: v for k, v in stock_info_dict.items() if v.volume > 0}

    # 实例化持仓变动回调
    trader_callback = TraderCallback(stock_info_dict)

    # 订阅持仓变化事件
    xt_trader.set_callback(trader_callback)

    # 基于持仓订阅市场数据
    update_quotes_subscription(stock_info_dict)

    # 启动事件循环
    xtdata.run()  # 启动事件驱动机制