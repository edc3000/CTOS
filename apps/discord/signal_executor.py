import sys
import os
import time
import asyncio
import discord
import json
from pathlib import Path
from datetime import datetime, timedelta
from tkinter import N
import pandas as pd
from typing import Dict, Any
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import discord

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
from apps.discord.discord_bot import DiscordSignalBot, DiscordSignalBotWithBackground
from apps.utils.utils import *
from apps.utils.logger import SignalLogger

class SignalExecutor:
    def __init__(self):
        # 初始化信号日志记录器
        self.signal_logger = SignalLogger(log_dir="logs", log_name="signal")
        
        # 加载信号配置
        self.config = self.load_config(os.path.join(os.path.dirname(__file__), "signal_config.json"))
    
        # 初始化engine
        self.engines = {}
        self.initialized = False
        if not self.initialize_engines():
            print("❌ 引擎初始化失败，无法启动系统")
            return
        self.engine = self.get_engine(self.config['exchange'], self.config['account_id'])
        
        # 加载discord bot
        self.discord_bot = DiscordSignalBotWithBackground()
        self.discord_bot.start_background()


    def load_config(self, config_file):
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"❌ 加载配置失败: {e}")
                
                
    def get_engine(self, exchange, account_id):
        """获取已初始化的引擎"""
        key = f"{exchange}_{account_id}"
        return self.engines.get(key)
                
    def initialize_engines(self):
        """初始化所有需要的引擎"""
        if self.initialized:
            return True
            
        print("🔧 初始化执行引擎...")
        
        # 收集所有需要的交易所+账户组合
        engine_keys = set()
        key = f"{self.config['exchange']}_{self.config['account_id']}"
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
                    strategy="signal_bot", 
                    strategy_detail="COMMON"
                )
                self.engines[key] = engine
                print(f"✅ 初始化引擎: {exchange}-{account_id}")
                success_count += 1
            except Exception as e:
                print(f"❌ 初始化引擎失败: {exchange}-{account_id} - {e}")
                
        
        self.initialized = True
        print(f"🎯 引擎初始化完成: {success_count}/{len(engine_keys)} 成功")
        return success_count > 0

    def section_signal(self):
        """
        处理截面策略信号（多线程优化版本）
        """
        def build_embed_message(messages: Dict) -> discord.Embed:
            """构建 Discord Embed 消息"""
            # 1. 根据涨跌设置 Emoji 和颜色
                # URL for a solid green and red image
            GREEN_IMAGE_URL = "https://via.placeholder.com/150/28a745/28a745.png"
            RED_IMAGE_URL = "https://via.placeholder.com/150/dc3545/dc3545.png"
            if messages['trend'] == "上涨":
                emoj = "📈"
                embed_color = discord.Color.green() # 上涨为绿色
                thumbnail_url = GREEN_IMAGE_URL
            else:
                emoj = "📉"
                embed_color = discord.Color.red() # 下跌为红色
                thumbnail_url = RED_IMAGE_URL
                
            embed = discord.Embed(
            title=f"{emoj} {messages['symbol']} ({messages['close']:.3f}) {messages['trend']} {messages['change_percent']:.2f}%",
            description=f"在 {messages['timeframe']} 级别触发提醒 ({messages['current_count']}/{messages['max_send_times']})",
            color=embed_color
            )
            
            # 2. 设置缩略图
            embed.set_thumbnail(url=messages['image_url'])
            
            # 3. 添加字段 (Fields) 来展示详细信息
            # 使用 inline=True 让字段并排显示，更美观
            embed.add_field(name=f"💰 价格: ${messages['close']}", value="", inline=True)
            embed.add_field(name='', value='', inline=False)
            embed.add_field(name=f"⏰ K线时间: {messages['kline']}", value="", inline=True)

            # 4. 设置页脚 (Footer) 来显示当前时间
            beijing_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            embed.set_footer(text=f"北京时间: {beijing_time}")
            return embed
        
        
        # 线程安全的缓存，使用 threading.Lock 保护
        self.signal_cache = defaultdict(int)
        self.last_processed_timestamp = {}
        self.cache_lock = threading.Lock()
        
        # 从配置中读取线程数，默认为 5
        max_workers = self.config['optional_changes'].get('max_workers', 5)
        
        def process_symbol_timeframe(symbol_info, symbol, timeframe, percent_threshold):
            """
            处理单个交易对的单个时间周期
            
            Args:
                symbol: 交易对符号
                timeframe: 时间周期
                percent_threshold: 涨跌幅阈值
            """
            try:
                # 获取K线数据
                klines = get_klines(self.engine, symbol, timeframe=timeframe)
                if klines is None or len(klines) == 0:
                    return None
                
                latest_kline = klines.iloc[0]
                kline_timestamp = int(latest_kline['trade_date'])
                kline_timestamp = format_ms_timestamp(kline_timestamp)
                
                # --- 线程安全的缓存管理 ---
                with self.cache_lock:
                    cache_key = (symbol, timeframe, kline_timestamp)
                    
                    # 清理旧缓存
                    last_ts = self.last_processed_timestamp.get((symbol, timeframe))
                    if last_ts and last_ts != kline_timestamp:
                        keys_to_remove = [
                            k for k in self.signal_cache 
                            if k[0] == symbol and k[1] == timeframe and k[2] < kline_timestamp
                        ]
                        for k in keys_to_remove:
                            del self.signal_cache[k]
                    
                    self.last_processed_timestamp[(symbol, timeframe)] = kline_timestamp
                    
                    # 检查发送次数限制
                    max_send_times = self.config['optional_changes'].get('max_send_times', 3)
                    current_count = self.signal_cache[cache_key]
                    
                    if current_count >= max_send_times:
                        print(f"🚫 {BeijingTime()} | {symbol}-{timeframe} (TS: {kline_timestamp}) "
                            f"的信号发送已达上限 ({max_send_times}次)。")
                        return None
                
                # --- 计算价格变化 ---
                open_price = float(latest_kline['open'])
                close_price = float(latest_kline['close'])
                volume = float(latest_kline['vol'])
                change = close_price - open_price
                change_percent = (change / open_price) * 100 if open_price != 0 else 0
                
                # --- 判断信号 ---
                trend = None
                
                if change_percent >= percent_threshold:
                    trend = "上涨"
                elif change_percent <= -percent_threshold:
                    trend = "下跌"
                
                if not trend:
                    print(f"ℹ️ {BeijingTime()} | {symbol} 在 {timeframe} k线内无显著变化: {change_percent:.2f}%")
                    return None
                
                # --- 生成消息 ---
                messages = {
                    "symbol": symbol,
                    "image_url": symbol_info['image_url'],
                    "close": close_price,
                    "timeframe": timeframe,
                    "kline": kline_timestamp,
                    "trend": trend,
                    "change_percent": abs(change_percent),
                    "current_count": current_count + 1,
                    "max_send_times": max_send_times
                    
                }
                embed = build_embed_message(messages)
                # --- 更新缓存计数（线程安全）---
                with self.cache_lock:
                    self.signal_cache[cache_key] += 1
                    self.signal_logger.info(f"✅ {BeijingTime()} | 准备为 {symbol}-{timeframe} (TS: {kline_timestamp}) "
                        f"发送信号。当前计数: {self.signal_cache[cache_key]}")
                
                # 📝 记录信号到日志文件
                self.signal_logger.log_signal(messages)
                
                return embed
                
            except Exception as e:
                self.signal_logger.info(f"❌ 处理 {symbol}-{timeframe} 时出错: {e}")
                return None
        
        # --- 主循环 ---
        while True:
            try:
                symbol_info = self.config['optional_changes']['symbol_info']
                
                # 创建任务列表
                tasks = []
                for info in symbol_info:
                    symbol = info['symbol']
                    timeframes = info.get('timeframe', [])
                    
                    for idx, timeframe in enumerate(timeframes):
                        percent_threshold = info['percent'][idx]
                        tasks.append((info, symbol, timeframe, percent_threshold))
                
                # 使用线程池执行任务
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    # 提交所有任务
                    future_to_task = {
                        executor.submit(process_symbol_timeframe, symbol_info, symbol, timeframe, percent): 
                        (symbol, timeframe)
                        for symbol_info, symbol, timeframe, percent in tasks
                    }
                    
                    # 处理完成的任务
                    for future in as_completed(future_to_task):
                        symbol, timeframe = future_to_task[future]
                        try:
                            embed = future.result()
                            if embed:
                                # 发送信号（假设 send_signal_sync 是线程安全的）
                                self.discord_bot.send_signal_sync(embed=embed)
                        except Exception as e:
                            print(f"❌ 获取 {symbol}-{timeframe} 结果时出错: {e}")
                
                # 等待下一个监控周期
                time.sleep(self.config["global_settings"]["monitor_interval"])
                
            except Exception as e:
                print(f"❌ 处理截面策略信号失败: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(5)  # 发生错误时短暂等待后重试
    


if __name__ == "__main__":
    executor = SignalExecutor()
    executor.section_signal()