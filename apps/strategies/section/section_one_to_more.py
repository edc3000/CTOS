import sys
import os
import time
import json
from pathlib import Path
from datetime import datetime, timedelta
from tkinter import N
import pandas as pd


def add_project_paths(project_name="ctos", subpackages=None):
    """
    自动查找项目根目录，并将其及常见子包路径添加到 sys.path。
    :param project_name: 项目根目录标识（默认 'ctos'）
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = None
    # 向上回溯，找到项目根目录
    path = current_dir
    while path != os.path.dirname(path):  # 一直回溯到根目录
        if os.path.basename(path) == project_name or os.path.exists(os.path.join(path, ".git")):
            project_root = path
            break
        path = os.path.dirname(path)
    if not project_root:
        raise RuntimeError(f"未找到项目根目录（包含 {project_name} 或 .git）")
    # 添加根目录
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    return project_root
# 执行路径添加
PROJECT_ROOT = add_project_paths()
print('PROJECT_ROOT: ', PROJECT_ROOT, 'CURRENT_DIR: ', os.path.dirname(os.path.abspath(__file__)))


from ctos.drivers.backpack.util import align_decimal_places, round_dynamic, round_to_two_digits, rate_price2order, cal_amount, BeijingTime
from ctos.core.runtime.ExecutionEngine import pick_exchange

class SectionStrategy:
    """截面策略"""
    
    def __init__(self, config_file="section_config.json"):
        self.config_file = os.path.join(os.path.dirname(__file__), config_file)
        self.config = self.load_config()
        self.engines = {}  # 按交易所+账户存储引擎
        self.running = True
        self.monitor_thread = None
        self.initialized = False
        
    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"❌ 加载配置失败: {e}")
                
    def initialize_engines(self):
        """初始化所有需要的引擎"""
        if self.initialized:
            return True
            
        print("🔧 初始化执行引擎...")
        
        # 收集所有需要的交易所+账户组合
        engine_keys = set()
        for strategy in self.config["strategies"]:
            if strategy["enabled"]:
                key = f"{strategy['exchange']}_{strategy['account_id']}"
                engine_keys.add(key)
        
        # 初始化所有引擎
        success_count = 0
        for key in engine_keys:
            exchange, account_id = key.split('_')
            account_id = int(account_id)
            
            try:
                exch, engine = pick_exchange(
                    cex=exchange, 
                    account=account_id, 
                    strategy="SimpleMartin", 
                    strategy_detail="COMMON"
                )
                self.engines[key] = engine
                print(f"✅ 初始化引擎: {exchange}-{account_id}")
                success_count += 1
            except Exception as e:
                print(f"❌ 初始化引擎失败: {exchange}-{account_id} - {e}")
                # 禁用使用该引擎的策略
                for strategy in self.config["strategies"]:
                    if (strategy["exchange"] == exchange and 
                        strategy["account_id"] == account_id):
                        strategy["enabled"] = False
                        print(f"⚠️ 禁用策略: {strategy['coin']} (引擎初始化失败)")
        
        self.initialized = True
        print(f"🎯 引擎初始化完成: {success_count}/{len(engine_keys)} 成功")
        return success_count > 0
    
    def get_engine(self, exchange, account_id):
        """获取已初始化的引擎"""
        key = f"{exchange}_{account_id}"
        return self.engines.get(key)
    
    def get_current_price(self, engine, coin):
        """获取当前价格"""
        try:
            price = engine.cex_driver.get_price_now(coin)
            return float(price) if price else None
        except Exception as e:
            print(f"❌ 获取价格失败 {coin}: {e}")
            return None
        
    def get_klines(self, engine, symbol, timeframe='1h', limit=200, start_time=None, end_time=None):
        """获取K线数据"""
        try:
            klines = engine.cex_driver.get_klines(symbol=symbol, timeframe=timeframe, limit=limit)
            return klines
        except Exception as e:
            print(f"❌ 获取K线失败 {symbol}: {e}")
            return None
        
    def analyze_klines(self, klines):
        """
        分析K线数据，返回涨跌幅和成交量信息
        
        参数:
            kline_data: DataFrame, dict 或 list，K线数据
                    - DataFrame: 包含 'open', 'close', 'volume' 等列
                    - dict: 应包含 'open', 'close', 'volume' 等字段
                    - list: 格式为 [timestamp, open, high, low, close, volume]
        
        返回:
            DataFrame 或 dict: 
                - 如果输入是DataFrame，返回添加了分析列的DataFrame
                - 如果输入是dict/list，返回包含分析结果的dict
        """
        # 处理字典格式的K线数据
        if isinstance(klines, dict):
            open_price = float(klines.get('open', 0))
            close_price = float(klines.get('close', 0))
            volume = float(klines.get('volume', 0))

        # 处理列表格式的K线数据 [timestamp, open, high, low, close, volume]
        elif isinstance(klines, pd.DataFrame):
            open_price = float(klines.iloc[0]['open'])
            close_price = float(klines.iloc[0]['close'])
            volume = float(klines.iloc[0]['vol'])

        else:
            raise ValueError("不支持的K线数据格式")

        # 计算涨跌额
        change = close_price - open_price

        # 计算涨跌幅（百分比）
        if open_price != 0:
            change_percent = (change / open_price) * 100
        else:
            change_percent = 0

        # 返回结果
        result = {
            'open': open_price,
            'close': close_price,
            'change': round(change, 4),
            'change_percent': round(change_percent, 2),
            'volume': volume
        }

        return result
    
    def check_signal(self, strategy):
        """检查单个策略的交易信号"""

        anchor_coin = strategy["anchor_coin"]
        exchange = strategy["exchange"]
        account_id = strategy["account_id"]
        
        if not strategy["enabled"]:
            return
        
        engine = self.get_engine(exchange, account_id)
        if not engine:
            return
        
        exchange_limits_info, err = engine.cex_driver.exchange_limits(symbol=anchor_coin)
        try:
            klines = self.get_klines(engine, anchor_coin, "30m")
            if klines is None:
                return
            kline_analysis = self.analyze_klines(klines[0])
        except Exception as e:
            print(f"❌ K线分析失败 {anchor_coin}: {e}")
            return
    
    def execute_strategy(self, strategy):
        """执行单个策略"""
        anchor_coin = strategy["anchor_coin"]
        exchange = strategy["exchange"]
        account_id = strategy["account_id"]
        
        if not strategy["enabled"]:
            return
        
        engine = self.get_engine(exchange, account_id)
        if not engine:
            return
        
        exchange_limits_info, err = engine.cex_driver.exchange_limits(symbol=anchor_coin)
        try:
            klines = self.get_klines(engine, anchor_coin, "30m")
            if klines is None:
                return
            kline_analysis = self.analyze_klines(klines[0])
            if kline_analysis['change_percent'] >= 0:
                trend = "上涨"
                print(f"📈 {BeijingTime()} | {anchor_coin} 30分钟K线分析: open {kline_analysis['open']}, close {kline_analysis['close']}, 涨额 {kline_analysis['change']}, 涨幅 {kline_analysis['change_percent']}%, 成交量 {kline_analysis['volume']}")
            else:
                trend = "下跌"
                print(f"📉 {BeijingTime()} | {anchor_coin} 30分钟K线分析: open {kline_analysis['open']}, close {kline_analysis['close']}, 跌额 {kline_analysis['change']}, 跌幅 {kline_analysis['change_percent']}%, 成交量 {kline_analysis['volume']}")

        except Exception as e:
            print(f"❌ K线分析失败 {anchor_coin}: {e}")
            return
    
        
    def run_strategies(self):
        """运行所有策略"""
        print(f"🚀 {BeijingTime()} | 启动策略执行")
        
        while self.running:
            try:
                if self.config["global_settings"]["emergency_stop"]:
                    print(f"🚨 {BeijingTime()} | 紧急停止触发")
                    break
                
                for strategy in self.config["strategies"]:
                    if strategy["enabled"]:
                        self.execute_strategy(strategy)
                
                time.sleep(self.config["global_settings"]["monitor_interval"])
                
            except KeyboardInterrupt:
                print(f"\n⏹️ {BeijingTime()} | 手动停止策略")
                break
            except Exception as e:
                print(f"❌ {BeijingTime()} | 策略运行异常: {e}")
                time.sleep(5)
        
        self.running = False
        print(f"🏁 {BeijingTime()} | 策略执行结束")
        
        
if __name__ == "__main__":
    strategy = SectionStrategy()
    if strategy.initialize_engines():
        strategy.run_strategies()