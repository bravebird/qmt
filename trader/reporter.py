from datetime import datetime
# 自定义
from trader.xt_acc import acc
from trader.xt_trader import xt_trader
from loggers import logger

xt_trader.subscribe(acc)

def generate_trading_report():
    order_type_dic = {23: "买入", 24: "卖出"}

    today = datetime.now().strftime("%Y-%m-%d")

    # 查询资产
    asset = xt_trader.query_stock_asset(account=acc)

    # 查询持仓
    positions = xt_trader.query_stock_positions(account=acc)

    # 查询当天成交记录
    trades = xt_trader.query_stock_trades(account=acc)

    # 生成报告

    report = f"\n\n交易报告 - {today}\n\n"
    report += "=" * 20

    report += f"\n资产情况:\n"
    report += f"    资产代码: {asset.account_id}， 总资产: {asset.total_asset}， 股票市值: {asset.market_value}， 可用现金: {asset.cash}\n"

    report += "=" * 20

    report += "\n持仓情况:\n"
    for position in positions:
        report += f"    股票代码: {position.stock_code}， 股票市值: {position.market_value}， 持股数量: {position.volume}， 平均成本: {position.avg_price}\n"

    report += "=" * 20

    report += "\n当日成交:\n"
    for trade in trades:
        traded_time = datetime.fromtimestamp(trade.traded_time)
        order_type = order_type_dic.get(trade.order_type, '未定义')
        report += f"    【{order_type}】股票代码: {trade.stock_code}， 成交金额: {trade.traded_amount}， 成交数量: {trade.traded_volume}， 成交价格: {trade.traded_price}， 成交时间: {traded_time}\n"

    report += "=" * 20

    logger.trader(report)

    return report

if __name__ == "__main__":
    report = generate_trading_report()
    print(report)