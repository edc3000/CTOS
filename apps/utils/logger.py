import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from datetime import datetime
from typing import Dict


class SignalLogger:
    """信号日志记录类"""
    
    def __init__(self, log_dir="logs", log_name="signal"):
        """
        初始化信号日志记录器
        
        Args:
            log_dir: 日志目录
            log_name: 日志文件名前缀
        """
        # 创建日志目录
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        # 创建logger
        self.logger = logging.getLogger(log_name)
        self.logger.setLevel(logging.INFO)
        
        # 避免重复添加handler
        if not self.logger.handlers:
            # 日志格式: 时间|交易对|周期|趋势|涨跌幅|价格|K线时间|发送次数
            formatter = logging.Formatter(
                '%(asctime)s|%(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            # 按天轮转的文件处理器,保留90天
            handler = TimedRotatingFileHandler(
                filename=log_path / f"{log_name}.log",
                when='midnight',
                interval=1,
                backupCount=90,
                encoding='utf-8'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def info(self, message: str):
        """记录信息日志"""
        self.logger.info(message)
    
    def log_signal(self, signal_data: Dict):
        """
        记录信号数据
        
        Args:
            signal_data: 包含以下字段的字典
                - symbol: 交易对
                - timeframe: 时间周期
                - trend: 趋势(上涨/下跌)
                - change_percent: 涨跌幅
                - close: 收盘价
                - kline: K线时间
                - current_count: 当前发送次数
                - max_send_times: 最大发送次数
        """
        log_message = (
            f"{signal_data['symbol']}|"
            f"{signal_data['timeframe']}|"
            f"{signal_data['trend']}|"
            f"{signal_data['change_percent']:.2f}%|"
            f"{signal_data['close']}|"
            f"{signal_data['kline']}|"
            f"{signal_data['current_count']}/{signal_data['max_send_times']}"
        )
        self.logger.info(log_message)