import sys
import os
import time
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

# 项目路径
_THIS_FILE = Path(__file__).resolve()
_PROJECT_ROOT = _THIS_FILE.parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ctos.drivers.backpack.util import align_decimal_places, round_dynamic, round_to_two_digits, rate_price2order, cal_amount, BeijingTime
from ctos.core.runtime.ExecutionEngine import pick_exchange



class HourlyLongShortStrategy:
    def __init__(self, driver, coins, capital_per_side=10000):
        """
        :param driver: 交易驱动 (OkxDriver / BackpackDriver)
        :param coins: 监控的币种列表，例如 ['BTC', 'ETH', 'SOL']
        :param capital_per_side: 多/空各分配的总资金
        """
        self.driver = driver
        self.coins = coins
        self.capital_per_side = capital_per_side
        self.positions = {}  # 记录开仓价格 {coin: {'side': str, 'entry': float}}

    def get_last_hour_returns(self):
        """获取上一小时的涨跌幅"""
        returns = {}
        for coin in self.coins:
            symbol, _, _ = self.driver._norm_symbol(coin)
            df, err = self.driver.get_klines(symbol, timeframe='1m', limit=60)
            if err or df is None or len(df) < 2:
                continue
            if isinstance(df, pd.DataFrame):
                close_price = float(df.iloc[0]['close'])
                open_price = float(df.iloc[-1]['open'])
            else:  # 兼容 list 格式
                open_price = float(df[0]['open'])
                close_price = float(df[-1]['close'])
            returns[coin] = (close_price - open_price) / open_price
        return returns

    def rebalance(self, engine=None):
        """每小时第一秒：决定开仓方向"""
        returns = self.get_last_hour_returns()
        if not returns:
            print("⚠️ 未能获取行情数据")
            return
        # 按涨幅排序
        sorted_coins = sorted(returns.items(), key=lambda x: x[1], reverse=True)
        n = len(sorted_coins)
        if n < 2:
            print("⚠️ 币种不足，跳过本轮")
            return
        half = n // 2
        longs = sorted_coins[:half]
        shorts = sorted_coins[half:]

        # 每个币分配资金
        long_cap = self.capital_per_side / max(1, len(longs))
        short_cap = self.capital_per_side / max(1, len(shorts))

        print(f"\n[{datetime.now()}] 开始新一轮调仓")
        # print("涨幅排名:", sorted_coins)

        # 多头
        usdt_amounts = []
        coins_to_deal = []
        for coin, ret in longs:
            price = self.driver.get_price_now(f"{coin}-USDT-SWAP")
            print(f"\r➡️ 做多 {coin}: {long_cap} USDT @ {price}, with return {ret*100:.4f}%", end='')
            self.positions[coin] = {"side": "long", "entry": price}
            coins_to_deal.append(coin)
            usdt_amounts.append(long_cap)
        # 空头
        for coin, ret in shorts:
            price = self.driver.get_price_now(f"{coin}-USDT-SWAP")
            print(f"\r⬅️ 做空 {coin}: {short_cap} USDT @ {price}, with return {ret*100:.4f}%", end='')
            self.positions[coin] = {"side": "short", "entry": price}
            coins_to_deal.append(coin)
            usdt_amounts.append(-short_cap)

        if engine is not None:
            focus_orders = engine.set_coin_position_to_target(usdt_amounts, coins_to_deal, soft=True)
            engine.focus_on_orders(coins_to_deal, focus_orders)
            while len(engine.watch_threads) > 0:
                time.sleep(1)

    def evaluate(self):
        """每小时最后10秒：评估盈亏"""
        print(f"\n[{datetime.now()}] 本小时结束，评估仓位表现")
        results = {}
        total_pnl = 0.0
        n = 0

        for coin, info in self.positions.items():
            side = info['side']
            entry = info['entry']
            now_price = self.driver.get_price_now(f"{coin}-USDT-SWAP")
            pnl_ratio = (now_price - entry) / entry if side == 'long' else (entry - now_price) / entry
            results[coin] = {"side": side, "entry": entry, "now": now_price, "pnl_ratio": pnl_ratio}
            print(f"\r📊 {coin:<6} {side:<5} 入场 {entry:.4f} → 现价 {now_price:.4f}, 收益 {pnl_ratio*100:.4f}%", end='')

            total_pnl += pnl_ratio
            n += 1

        avg_pnl = total_pnl / n if n > 0 else 0.0
        print(f"\n📈 本小时总体平均收益率: {avg_pnl*100:.4f}%")

        return results, avg_pnl

def main():
        # 自动用当前文件名（去除后缀）作为默认策略名，细节默认为COMMON
    default_strategy = os.path.splitext(os.path.basename(__file__))[0].upper()
    exch1, engine1 = pick_exchange('okx', 0, strategy=default_strategy, strategy_detail="COMMON")
    exch2, engine2 = pick_exchange('bp', 2, strategy=default_strategy, strategy_detail="COMMON")
    all_coins_in_cex, _  = engine2.cex_driver.symbols()
    print(all_coins_in_cex, len(all_coins_in_cex))
    all_coins = []
    for x in all_coins_in_cex:
        if x.find('-') != -1:
            if x[:x.find('-')].lower() in rate_price2order.keys():
                all_coins.append(x[:x.find('-')].lower())
        else:
            if x[:x.find('_')].lower() in rate_price2order.keys():
                all_coins.append(x[:x.find('_')].lower())
    print(all_coins, len(all_coins))
    coins = [x.lower() for x in all_coins]  # 示例
    strat = HourlyLongShortStrategy(engine1.cex_driver, coins, 1000)
    clear_flag = False
    while True:
        now = datetime.now()
        # 整点 + 1 秒：开仓
        if now.minute == 0 and clear_flag:
            strat.rebalance()
            # strat.rebalance(engine2)
            clear_flag = False
        # 整点 - 10 秒：评估
        if now.minute == 59 and now.second >= 50:
            clear_flag = True
            # engine2.revoke_all_orders()
            strat.evaluate()
            time.sleep(15)  # 避免重复触发
        time.sleep(1)

if __name__ == "__main__":
    main()
