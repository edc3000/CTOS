import sys
import os
import time
from collections import defaultdict
from datetime import datetime

def format_ms_timestamp(ms_timestamp: int) -> str:
    """
    将Unix毫秒时间戳格式化为 'YYYY-MM-DD HH:MM:SS' 格式的字符串。
    """
    try:
        # 将毫秒转换为秒
        seconds_timestamp = ms_timestamp / 1000.0
        # 从时间戳创建datetime对象
        dt_object = datetime.fromtimestamp(seconds_timestamp)
        # 格式化为字符串
        return dt_object.strftime('%Y-%m-%d %H:%M:%S') #
    except (ValueError, TypeError):
        # 如果时间戳格式错误，返回原始值
        return str(ms_timestamp)


def get_current_price(engine, symbol):
    """获取当前价格"""
    try:
        price = engine.cex_driver.get_price_now(symbol)
        return float(price) if price else None
    except Exception as e:
        print(f"❌ 获取价格失败 {symbol}: {e}")
        return None
    
def get_klines(engine, symbol, timeframe='1h', limit=200, start_time=None, end_time=None):
    """获取K线数据"""
    try:
        klines = engine.cex_driver.get_klines(symbol=symbol, timeframe=timeframe, limit=limit)
        return klines[0]
    except Exception as e:
        print(f"❌ 获取K线失败 {symbol}: {e}")
        return None