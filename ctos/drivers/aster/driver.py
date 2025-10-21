# -*- coding: utf-8 -*-
# ctos/drivers/aster/driver.py
# Aster DEX driver that provides unified interface for Aster protocol trading.
# Compatible with older Python (no dataclasses/Protocol).

from __future__ import print_function
import math
import json
import os
import sys
import time
from typing import Dict, List, Tuple, Optional, Any, Union

def _add_project_path():
    """添加项目路径到sys.path，支持多种运行方式"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, '../../..'))
    
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    return project_root

# 执行路径添加
_PROJECT_ROOT = _add_project_path()

# Import syscall base
try:
    # 包内正常导入
    from ctos.core.kernel.syscalls import TradingSyscalls
except ImportError:
    # 单文件执行时，修正 sys.path 再导入
    import os, sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
    from ctos.core.kernel.syscalls import TradingSyscalls

# Import account reader
try:
    from configs.account_reader import get_aster_credentials, list_accounts
except ImportError:
    # 如果无法导入，使用备用方案
    def get_aster_credentials(account='main'):
        # 这里需要根据实际的Aster配置进行调整
        return {
            'private_key': 'your_private_key_here',
            'rpc_url': 'https://rpc.aster.xyz',
            'chain_id': 1
        }
    
    def list_accounts(exchange='aster'):
        return ['main', 'sub1', 'sub2']  # 默认账户列表

def get_account_name_by_id(account_id=0, exchange='aster'):
    """
    根据账户ID获取账户名称
    
    Args:
        account_id: 账户ID
        exchange: 交易所名称
        
    Returns:
        str: 账户名称
    """
    try:
        accounts = list_accounts(exchange)
        
        if account_id < len(accounts):
            return accounts[account_id]
        else:
            print(f"警告: 账户ID {account_id} 超出范围，可用账户: {accounts}")
            return accounts[0] if accounts else 'main'
            
    except Exception as e:
        print(f"获取账户名称失败: {e}，使用默认映射")
        # 回退到默认映射
        default_mapping = {0: 'main', 1: 'sub1', 2: 'sub2'}
        return default_mapping.get(account_id, 'main')

def init_AsterClient(symbol="ETH-USDT", account_id=0, show=False):
    """
    初始化Aster客户端
    
    Args:
        symbol: 交易对符号
        account_id: 账户ID，根据配置文件中的账户顺序映射 (0=第一个账户, 1=第二个账户, ...)
        show: 是否显示调试信息
        
    Returns:
        AsterClient: Aster客户端实例
        
    Note:
        账户ID映射基于configs/account.yaml中accounts.aster下的账户顺序
        例如: 如果配置文件中有['main', 'sub1', 'sub2']，则account_id=0对应main，account_id=1对应sub1
    """
    if symbol.find('-') == -1:
        symbol = f'{symbol.upper()}-USDT'
    
    # 从配置文件动态获取账户名称
    account_name = get_account_name_by_id(account_id, 'aster')
    
    try:
        # 使用账户获取器获取认证信息
        credentials = get_aster_credentials(account_name)
        
        if show:
            print(f"使用Aster账户: {account_name} (ID: {account_id})")
            print(f"认证字段: {list(credentials.keys())}")
        
        # 这里需要根据实际的Aster客户端实现进行调整
        return AsterClient(
            symbol=symbol, 
            private_key=credentials['private_key'],
            rpc_url=credentials['rpc_url'],
            chain_id=credentials['chain_id']
        )
    except Exception as e:
        print(f"获取Aster账户 {account_name} 认证信息失败: {e}")
        # 回退到默认配置
        return AsterClient(
            symbol=symbol, 
            private_key='your_private_key_here',
            rpc_url='https://rpc.aster.xyz',
            chain_id=1
        )

class AsterClient:
    """
    Aster DEX客户端模拟类
    这里需要根据实际的Aster SDK进行实现
    """
    def __init__(self, symbol, private_key, rpc_url, chain_id):
        self.symbol = symbol
        self.private_key = private_key
        self.rpc_url = rpc_url
        self.chain_id = chain_id
        # 这里需要初始化实际的Aster SDK客户端
        
    def get_price_now(self, symbol):
        """获取当前价格"""
        # 模拟实现，需要替换为实际的Aster API调用
        return 4480.6
        
    def get_orderbook(self, symbol, level=50):
        """获取订单簿"""
        # 模拟实现，需要替换为实际的Aster API调用
        return {
            "symbol": symbol,
            "bids": [["4480.5", "100.0"], ["4480.4", "200.0"]],
            "asks": [["4480.6", "150.0"], ["4480.7", "250.0"]]
        }
        
    def get_kline(self, timeframe, limit, symbol):
        """获取K线数据"""
        # 模拟实现，需要替换为实际的Aster API调用
        import pandas as pd
        import numpy as np
        
        # 生成模拟K线数据
        timestamps = [int(time.time() * 1000) - i * 3600000 for i in range(limit)]
        prices = [4480.6 + np.random.normal(0, 10) for _ in range(limit)]
        
        data = []
        for i, ts in enumerate(timestamps):
            price = prices[i]
            data.append({
                'ts': ts,
                'open': price + np.random.normal(0, 2),
                'high': price + abs(np.random.normal(0, 5)),
                'low': price - abs(np.random.normal(0, 5)),
                'close': price,
                'volume': np.random.uniform(1000, 10000)
            })
        
        df = pd.DataFrame(data)
        return df, None
        
    def place_order(self, symbol, side, order_type, quantity, price=None, **kwargs):
        """下单"""
        # 模拟实现，需要替换为实际的Aster API调用
        order_id = f"aster_{int(time.time() * 1000)}"
        return order_id, None
        
    def amend_order(self, orderId, symbol=None, **kwargs):
        """修改订单"""
        # 模拟实现，需要替换为实际的Aster API调用
        return orderId, None
        
    def revoke_order(self, order_id):
        """撤销订单"""
        # 模拟实现，需要替换为实际的Aster API调用
        return True, None
        
    def get_order_status(self, order_id, symbol=None):
        """获取订单状态"""
        # 模拟实现，需要替换为实际的Aster API调用
        return {
            'orderId': order_id,
            'symbol': symbol or 'ETH-USDT',
            'side': 'buy',
            'orderType': 'limit',
            'price': 3584.12,
            'quantity': 0.01,
            'filledQuantity': 0.0,
            'status': 'live',
            'timeInForce': None,
            'postOnly': None,
            'reduceOnly': False,
            'clientId': '',
            'createdAt': int(time.time() * 1000),
            'updatedAt': int(time.time() * 1000),
            'raw': {}
        }, None
        
    def get_open_orders(self, symbol=None, onlyOrderId=True):
        """获取未成交订单"""
        # 模拟实现，需要替换为实际的Aster API调用
        if onlyOrderId:
            return [f"aster_{int(time.time() * 1000)}"], None
        else:
            return [{
                'orderId': f"aster_{int(time.time() * 1000)}",
                'symbol': symbol or 'ETH-USDT',
                'side': 'buy',
                'orderType': 'limit',
                'price': 3584.12,
                'quantity': 0.01,
                'filledQuantity': 0.0,
                'status': 'live',
                'timeInForce': None,
                'postOnly': None,
                'reduceOnly': False,
                'clientId': '',
                'createdAt': int(time.time() * 1000),
                'updatedAt': int(time.time() * 1000),
                'raw': {}
            }], None
            
    def revoke_orders(self, symbol=None):
        """撤销所有订单"""
        # 模拟实现，需要替换为实际的Aster API调用
        return {"ok": True, "raw": "orders_cancelled"}
        
    def fetch_balance(self, currency='USDT'):
        """获取余额"""
        # 模拟实现，需要替换为实际的Aster API调用
        return 3651.262698055444
        
    def get_position(self, symbol=None):
        """获取持仓"""
        # 模拟实现，需要替换为实际的Aster API调用
        return {
            'symbol': symbol or 'ETH-USDT',
            'positionId': f"pos_{int(time.time() * 1000)}",
            'side': 'long',
            'quantity': 1.0,
            'entryPrice': 4480.0,
            'markPrice': 4480.6,
            'pnlUnrealized': 0.6,
            'pnlRealized': 0.0,
            'leverage': 1.0,
            'liquidationPrice': 0.0,
            'ts': int(time.time() * 1000)
        }, None
        
    def get_market(self, instId='', all=True, condition=None):
        """获取市场信息"""
        # 模拟实现，需要替换为实际的Aster API调用
        symbols = [
            {'instId': 'ETH-USDT', 'instType': 'SPOT'},
            {'instId': 'BTC-USDT', 'instType': 'SPOT'},
            {'instId': 'SOL-USDT', 'instType': 'SPOT'}
        ]
        return symbols, None
        
    def get_exchange_info(self, instType='SPOT', symbol=None):
        """获取交易所信息"""
        # 模拟实现，需要替换为实际的Aster API调用
        return {
            'code': '0',
            'data': [{
                'instId': symbol or 'ETH-USDT',
                'instType': instType,
                'tickSz': '0.01',
                'lotSz': '0.001',
                'minSz': '0.001',
                'ctVal': '0',
                'lever': '0',
                'state': 'live'
            }],
            'msg': ''
        }, None
        
    def get_funding_rate(self, symbol, instType):
        """获取资金费率"""
        # 模拟实现，需要替换为实际的Aster API调用
        return {
            'code': '0',
            'data': [{
                'instId': symbol,
                'instType': instType,
                'fundingRate': '-0.0000427659650809',
                'fundingTime': str(int(time.time() * 1000) + 3600000),
                'nextFundingRate': '-0.0000427659650809',
                'nextFundingTime': str(int(time.time() * 1000) + 3600000)
            }],
            'msg': ''
        }, None

class AsterDriver(TradingSyscalls):
    """
    CTOS Aster DEX driver.
    提供与OKX driver相同的接口，适配Aster协议交易。
    主要方法包括:
      - get_price_now('eth') -> 获取当前价格
      - get_kline(tf, N, 'ETH-USDT') -> 返回K线数据
      - place_order(...) -> 下单
      - revoke_orders(...) -> 撤单
      - fetch_balance(), get_position() -> 账户和持仓信息
    """

    def __init__(self, aster_client=None, mode="spot", default_quote="USDT",
                 price_scale=1e-8, size_scale=1e-8, account_id=0):
        """
        初始化Aster DEX驱动
        
        Args:
            aster_client: 可选的Aster客户端实例。如果为None，将尝试使用默认配置初始化
            mode: "spot" 或 "perp"。Aster主要支持现货交易
            default_quote: 当用户传入'BTC'而没有'-USDT'时的默认计价货币
            price_scale: 价格精度缩放因子
            size_scale: 数量精度缩放因子
            account_id: 账户ID，根据配置文件中的账户顺序映射
        """
        self.cex = 'ASTER'
        self.quote_ccy = 'USDT'
        self.account_id = account_id
        
        if aster_client is None:
            try:
                self.aster = init_AsterClient(account_id=account_id)
                print(f"✓ Aster Driver初始化成功 (账户ID: {account_id})")
            except Exception as e:
                print(f"✗ Aster Driver初始化失败 (账户ID: {account_id}): {e}")
                self.aster = None
        else:
            self.aster = aster_client
            print(f"✓ Aster Driver使用外部客户端 (账户ID: {account_id})")
            
        self.mode = (mode or "spot").lower()
        self.default_quote = default_quote or "USDT"
        self.price_scale = price_scale
        self.size_scale = size_scale
        self.load_exchange_trade_info()
        self.order_id_to_symbol = {}

    def save_exchange_trade_info(self):
        """保存交易所交易信息到本地文件"""
        with open(os.path.dirname(os.path.abspath(__file__)) + '/exchange_trade_info.json', 'w') as f:
            json.dump(self.exchange_trade_info, f)

    def load_exchange_trade_info(self):
        """从本地文件加载交易所交易信息"""
        if not os.path.exists(os.path.dirname(os.path.abspath(__file__)) + '/exchange_trade_info.json'):
            self.exchange_trade_info = {}
            return
        with open(os.path.dirname(os.path.abspath(__file__)) + '/exchange_trade_info.json', 'r') as f:
            self.exchange_trade_info = json.load(f)

    # -------------- helpers --------------
    def _norm_symbol(self, symbol):
        """
        标准化交易对符号
        接受 'BTC-USDT', 'BTC/USDT', 'btc', 'BTC-USDT-SWAP' 等格式
        返回完整的Aster符号字符串 (例如 'BTC-USDT' 当在现货模式时)
        以及元组 (base, quote)
        
        Args:
            symbol: 交易对符号
            
        Returns:
            tuple: (完整符号, 基础货币, 计价货币)
        """
        s = str(symbol or "").replace("/", "-").upper()
        if "-" in s:
            parts = s.split("-")
            base = parts[0]
            quote = parts[1] if len(parts) > 1 else self.default_quote
        else:
            base = s
            quote = self.default_quote

        full = base + "-" + quote
        # Aster主要支持现货交易，不需要SWAP后缀
        return full, base.lower(), quote.upper()

    # -------------- ref-data / meta --------------
    def symbols(self, instType='SPOT'):
        """
        返回指定类型的交易对列表
        
        Args:
            instType: 'SPOT' | 'PERP' 等，默认 'SPOT'
            
        Returns:
            tuple: (list[str], error) 如 (['BTC-USDT', 'ETH-USDT', ...], None)
        """
        if not hasattr(self.aster, 'get_market'):
            # 兜底：无法从底层获取时，返回少量默认
            return ["BTC-USDT", "ETH-USDT", "SOL-USDT"] if str(instType).upper() == 'SPOT' else [], None

        try:
            condition = str(instType).upper() if instType else None
            data, err = self.aster.get_market(instId='', all=True, condition=condition)
            if err:
                return [], err
                
            # 提取并去重
            symbols = []
            seen = set()
            for item in data or []:
                inst_id = item.get('instId') if isinstance(item, dict) else None
                if not inst_id:
                    continue
                if condition and condition not in inst_id:
                    continue
                if inst_id not in seen:
                    seen.add(inst_id)
                    symbols.append(inst_id)
            return symbols, None
        except Exception as e:
            return [], e

    def exchange_limits(self, symbol=None, instType='SPOT'):
        """
        获取交易所限制信息，包括价格精度、数量精度、最小下单数量等
        
        Args:
            symbol: 交易对符号，如 'ETH-USDT'，如果为None则返回全类型数据
            instType: 产品类型，默认为 'SPOT'
            
        Returns:
            tuple: (dict, error) 包含限制信息的字典
        """
        if symbol:
            symbol, _, _ = self._norm_symbol(symbol)
            if symbol in self.exchange_trade_info:
                return self.exchange_trade_info[symbol], None
                
        if not hasattr(self.aster, 'get_exchange_info'):
            return {"error": "aster client lacks get_exchange_info method"}
        
        try:
            # 调用 get_exchange_info 获取数据
            success, error = self.aster.get_exchange_info(instType=instType, symbol=symbol)
            
            if error:
                return {"error": f"API调用失败: {error}"}
            
            if not success or success.get('code') != '0':
                return {"error": f"API返回错误: {success.get('msg', '未知错误')}"}
            
            data_list = success.get('data', [])
            if not data_list:
                return {"error": "未获取到数据"}
            
            # 如果指定了symbol，返回单一币种信息
            if symbol:
                if len(data_list) == 1:
                    item = data_list[0]
                    limits = self._extract_limits_from_item(item)
                    if limits and 'error' not in limits:
                        self.exchange_trade_info[symbol] = limits
                        self.save_exchange_trade_info()
                    return limits, None
                else:
                    return None, {"error": f"未找到指定交易对 {symbol} 的信息"}
            
            # 如果没有指定symbol，返回全类型数据数组
            result = []
            for item in data_list:
                limits = self._extract_limits_from_item(item)
                if limits and 'error' in limits:
                    continue
                ticker_symbol = item.get('instId', '')
                if instType.upper() in ticker_symbol.upper():
                    if limits and 'error' not in limits:
                        result.append(limits)
                        self.exchange_trade_info[ticker_symbol] = limits
            self.save_exchange_trade_info()
            return result, None
            
        except Exception as e:
            return None, {"error": f"处理数据时发生异常: {str(e)}"}
    
    def _extract_limits_from_item(self, item):
        """
        从单个数据项中提取限制信息
        
        Args:
            item: 单个交易对数据项
            
        Returns:
            dict: 包含限制信息的字典
        """
        try:
            # 提取基本字段
            tick_sz = item.get('tickSz', '0')
            lot_sz = item.get('lotSz', '0') 
            min_sz = item.get('minSz', '0')
            ct_val = item.get('ctVal', '0')
            lever = item.get('lever', '0')
            
            # 转换为浮点数
            tick_sz_float = float(tick_sz) if tick_sz and tick_sz != '0' else 0.0
            lot_sz_float = float(lot_sz) if lot_sz and lot_sz != '0' else 0.0
            min_sz_float = float(min_sz) if min_sz and min_sz != '0' else 0.0
            ct_val_float = float(ct_val) if ct_val and ct_val != '0' else 0.0
            lever_float = float(lever) if lever and lever != '0' else 0.0
            
            return {
                'symbol': item.get('instId', ''),
                'instType': item.get('instType', ''),
                'price_precision': tick_sz_float,  # 下单价格精度
                'size_precision': lot_sz_float,    # 下单数量精度
                'min_order_size': min_sz_float,    # 最小下单数量
                'contract_value': ct_val_float,    # 合约面值（仅适用于交割/永续/期权）
                'max_leverage': lever_float,       # 最大杠杆倍数（不适用于币币、期权）
                'state': item.get('state', ''),    # 交易对状态
                'raw': item  # 原始数据
            }
        except Exception as e:
            print(f"{item.get('instId', '')},解析数据项时发生异常: {str(e)}")
            return {"error": f"解析数据项时发生异常: {str(e)}"}

    def fees(self, symbol='ETH-USDT', instType='SPOT', keep_origin=False):
        """
        统一资金费率返回结构，标准化为"每小时资金费率"。
        注意：Aster是现货DEX，通常没有资金费率，这里返回0
        
        Args:
            symbol: 交易对符号
            instType: 产品类型
            keep_origin: 是否保持原始格式
            
        Returns:
            tuple: (dict, error) 费率信息字典
        """
        full, _, _ = self._norm_symbol(symbol)
        if not hasattr(self.aster, "get_funding_rate"):
            # Aster是现货DEX，没有资金费率
            result = {
                'symbol': full,
                'instType': instType,
                'fundingRate_hourly': 0.0,
                'fundingRate_period': 0.0,
                'period_hours': 0.0,
                'fundingTime': 0,
                'raw': {'note': 'Aster is a spot DEX, no funding rate'},
            }
            return result, None

        raw, err = self.aster.get_funding_rate(full, instType)
        if keep_origin:
            return raw, err
        if err:
            return None, err

        try:
            # 处理资金费率数据
            data_list = None
            if isinstance(raw, dict):
                data_list = raw.get('data')
            if isinstance(data_list, list) and data_list:
                d0 = data_list[0]
                fr_period = float(d0.get('fundingRate')) if d0.get('fundingRate') not in (None, '') else 0.0

                # 推断周期：使用 nextFundingTime - fundingTime，若不可用，默认8小时
                ts = d0.get('fundingTime') or d0.get('ts')
                nts = d0.get('nextFundingTime')
                if ts is not None and nts is not None:
                    period_hours = max(1.0, (float(nts) - float(ts)) / 1000.0 / 3600.0)
                else:
                    period_hours = 8.0

                hourly = fr_period / period_hours if period_hours else fr_period
                result = {
                    'symbol': d0.get('instId', full),
                    'instType': d0.get('instType', instType),
                    'fundingRate_hourly': hourly,
                    'fundingRate_period': fr_period,
                    'period_hours': period_hours,
                    'fundingTime': int(d0.get('fundingTime') or d0.get('ts') or 0),
                    'raw': raw,
                }
                return result, None

            # 回退：原样返回
            return {'symbol': full, 'instType': instType, 'fundingRate_hourly': None, 'fundingRate_period': None, 'period_hours': None, 'fundingTime': None, 'raw': raw}, None
        except Exception as e:
            return None, e

    # -------------- market data --------------
    def get_price_now(self, symbol='ETH-USDT'):
        """
        获取当前价格
        
        Args:
            symbol: 交易对符号，如 'ETH-USDT' 或 'eth'
            
        Returns:
            float: 当前价格
        """
        full, base, _ = self._norm_symbol(symbol)
        if hasattr(self.aster, "get_price_now"):
            return float(self.aster.get_price_now(full))
        # Fallback: try full symbol if your client expects it
        if hasattr(self.aster, "get_price"):
            return float(self.aster.get_price(full))
        raise NotImplementedError("aster client needs get_price_now(base) or get_price(symbol)")

    def get_orderbook(self, symbol='ETH-USDT', level=50):
        """
        获取订单簿
        
        Args:
            symbol: 交易对符号
            level: 订单簿深度
            
        Returns:
            dict: {'symbol': 'ETH-USDT', 'bids': [...], 'asks': [...]}
        """
        full, _, _ = self._norm_symbol(symbol)
        if hasattr(self.aster, "get_orderbook"):
            raw = self.aster.get_orderbook(full, int(level))
            bids = raw.get("bids", []) if isinstance(raw, dict) else []
            asks = raw.get("asks", []) if isinstance(raw, dict) else []
            return {"symbol": full, "bids": bids, "asks": asks}
        raise NotImplementedError("aster client lacks get_orderbook(symbol, level)")

    def get_klines(self, symbol='ETH-USDT', timeframe='1h', limit=200):
        """
        获取K线数据，标准化为字典列表格式:
        [{'ts': ts_ms, 'open': o, 'high': h, 'low': l, 'close': c, 'volume': v}, ...]
        
        Args:
            symbol: 交易对符号
            timeframe: 时间周期
            limit: 数据条数
            
        Returns:
            tuple: (data, error) 其中data是K线数据列表或DataFrame
        """
        full, _, _ = self._norm_symbol(symbol)
        if not hasattr(self.aster, "get_kline"):
            raise NotImplementedError("aster client lacks get_kline(tf, limit, symbol)")

        raw, err = self.aster.get_kline(str(timeframe), int(limit), full)
        if not err:
            return raw, err
        else:
            return None, err

    # -------------- trading --------------
    def place_order(self, symbol, side, order_type, size, price=None, client_id=None, **kwargs):
        """
        下单，将输入标准化到Aster客户端
        
        Args:
            symbol: 交易对符号
            side: 'buy'|'sell'
            order_type: 'market'|'limit'
            size: 数量
            price: 价格（限价单必需）
            client_id: 客户端订单ID
            **kwargs: 其他参数
            
        Returns:
            tuple: (order_id, error)
        """
        full, _, _ = self._norm_symbol(symbol)
        if not hasattr(self.aster, "place_order"):
            raise NotImplementedError("aster client lacks place_order(...)")

        order_id, err = self.aster.place_order(
            symbol=full,
            side=str(side).lower(),
            order_type=str(order_type).lower(),
            quantity=float(size),
            price=price,
            **kwargs
        )
        return order_id, err

    def buy(self, symbol, size, price=None, order_type="limit", **kwargs):
        """
        买入订单的便捷包装方法
        
        Args:
            symbol: 交易对符号，如 'ETH-USDT' 或 'eth'
            size: 数量
            price: 限价单的价格，市价单可省略
            order_type: 'limit' | 'market' | 'post_only'
            **kwargs: 其他参数
            
        Returns:
            tuple: (order_id, error)
        """
        return self.place_order(
            symbol=symbol,
            side="buy",
            order_type=str(order_type).lower(),
            size=float(size),
            price=price,
            **kwargs,
        )

    def sell(self, symbol, size, price=None, order_type="limit", **kwargs):
        """
        卖出订单的便捷包装方法
        
        Args:
            symbol: 交易对符号，如 'ETH-USDT' 或 'eth'
            size: 数量
            price: 限价单的价格，市价单可省略
            order_type: 'limit' | 'market' | 'post_only'
            **kwargs: 其他参数
            
        Returns:
            tuple: (order_id, error)
        """
        return self.place_order(
            symbol=symbol,
            side="sell",
            order_type=str(order_type).lower(),
            size=float(size),
            price=price,
            **kwargs,
        )

    def amend_order(self, order_id, symbol=None, **kwargs):
        """
        修改订单
        
        Args:
            order_id: 订单ID
            symbol: 交易对符号
            **kwargs: 其他参数
            
        Returns:
            tuple: (order_id, error)
        """
        if hasattr(self.aster, "amend_order"):
            order_id, err = self.aster.amend_order(orderId=order_id, symbol=symbol, **kwargs)
            return order_id, err
        if hasattr(self.aster, "modify_order"):
            order_id, err = self.aster.modify_order(orderId=order_id, symbol=symbol, **kwargs)
            return order_id, err
        raise NotImplementedError("aster client lacks amend_order/modify_order")

    def revoke_order(self, order_id):
        """
        撤销单个订单
        
        Args:
            order_id: 订单ID
            
        Returns:
            tuple: (success, error)
        """
        if hasattr(self.aster, "revoke_order"):
            success, error = self.aster.revoke_order(order_id=order_id)
            return success, error
        raise NotImplementedError("aster client lacks revoke_order(order_id=...)")

    def get_order_status(self, order_id, symbol=None, keep_origin=False):
        """
        获取订单状态
        
        Args:
            order_id: 订单ID
            symbol: 交易对符号
            keep_origin: 是否保持原始格式
            
        Returns:
            tuple: (normalized_order, error)
        """
        if hasattr(self.aster, "get_order_status"):
            success, error = self.aster.get_order_status(order_id=order_id, symbol=symbol)
            if keep_origin:
                return success, error

            if error:
                print(f"order_status {order_id} success: {success} error: {error}")
                return None, error

            od = None
            if isinstance(success, dict):
                # 处理Aster返回格式
                od = success
            if not isinstance(od, dict):
                return None, None

            def _val(k):
                v = od.get(k)
                return v

            def _float(v):
                try:
                    return float(v)
                except Exception:
                    return None

            normalized = {
                'orderId': _val('orderId'),
                'symbol': _val('symbol'),
                'side': (str(_val('side')).lower() if _val('side') is not None else None),
                'orderType': (str(_val('orderType')).lower() if _val('orderType') is not None else None),
                'price': _float(_val('price')),
                'quantity': _float(_val('quantity')),
                'filledQuantity': _float(_val('filledQuantity') or 0.0),
                'status': _val('status'),
                'timeInForce': _val('timeInForce'),
                'postOnly': _val('postOnly'),
                'reduceOnly': _val('reduceOnly'),
                'clientId': _val('clientId'),
                'createdAt': int(_val('createdAt') or 0) if _val('createdAt') else None,
                'updatedAt': int(_val('updatedAt') or 0) if _val('updatedAt') else None,
                'raw': od,
            }
            return normalized, None
        raise NotImplementedError("aster client lacks get_order_status(order_id=...)")

    def get_open_orders(self, symbol='ETH-USDT', instType='SPOT', onlyOrderId=True, keep_origin=True):
        """
        获取未成交订单
        
        Args:
            symbol: 交易对符号
            instType: 产品类型
            onlyOrderId: 是否只返回订单ID
            keep_origin: 是否保持原始格式
            
        Returns:
            tuple: (orders, error)
        """
        if hasattr(self.aster, "get_open_orders"):
            success, error = self.aster.get_open_orders(symbol=symbol, onlyOrderId=onlyOrderId)
            if onlyOrderId or keep_origin:
                return success, error

            if error:
                return None, error

            # success 应为 list[dict]
            orders = success or []
            normalized = []
            for od in orders:
                if not isinstance(od, dict):
                    continue
                def _f(key, default=None):
                    v = od.get(key)
                    return v if v is not None else default
                    
                # 解析字段
                order_id = _f('orderId')
                sym = _f('symbol')
                side = str(_f('side', '')).lower() or None
                order_type = str(_f('orderType', '')).lower() or None
                try:
                    price = float(_f('price')) if _f('price') not in (None, '') else None
                except Exception:
                    price = None
                try:
                    qty = float(_f('quantity')) if _f('quantity') not in (None, '') else None
                except Exception:
                    qty = None
                try:
                    filled = float(_f('filledQuantity') or 0.0)
                except Exception:
                    filled = None
                status = _f('status')
                tif = _f('timeInForce')
                post_only = _f('postOnly')
                reduce_only = _f('reduceOnly')
                client_id = _f('clientId')
                try:
                    created_at = int(_f('createdAt') or 0)
                except Exception:
                    created_at = None
                try:
                    updated_at = int(_f('updatedAt') or 0)
                except Exception:
                    updated_at = None

                normalized.append({
                    'orderId': order_id,
                    'symbol': sym,
                    'side': side,
                    'orderType': order_type,
                    'price': price,
                    'quantity': qty,
                    'filledQuantity': filled,
                    'status': status,
                    'timeInForce': tif,
                    'postOnly': post_only,
                    'reduceOnly': reduce_only,
                    'clientId': client_id,
                    'createdAt': created_at,
                    'updatedAt': updated_at,
                    'raw': od,
                })
            return normalized, None
        raise NotImplementedError("aster client lacks get_open_orders")

    def cancel_all(self, symbol='ETH-USDT', order_ids=[]):
        """
        撤销所有订单
        
        Args:
            symbol: 交易对符号
            order_ids: 特定订单ID列表
            
        Returns:
            dict: 撤销结果
        """
        if hasattr(self.aster, "revoke_orders"):
            if not symbol and len(order_ids) > 0:
                for ord in order_ids:
                    resp = self.revoke_order(ord)
                    return {"ok": True, "raw": resp}
            if symbol:
                full, _, _ = self._norm_symbol(symbol)
                resp = self.aster.revoke_orders(symbol=full)
            else:
                resp = self.aster.revoke_orders()
            return {"ok": True, "raw": resp}

        raise NotImplementedError("aster client lacks revoke_orders/cancel_all")

    # -------------- account --------------
    def fetch_balance(self, currency='USDT'):
        """
        获取余额信息，返回简单的扁平字典
        
        Args:
            currency: 货币类型
            
        Returns:
            float: 余额数量
        """
        if hasattr(self.aster, "fetch_balance"):
            try:
                raw = self.aster.fetch_balance(currency)
                return raw
            except Exception as e:
                return e
        raise NotImplementedError("aster client lacks fetch_balance")

    def get_position(self, symbol=None, keep_origin=False, instType='SPOT'):
        """
        获取持仓信息
        
        Args:
            symbol: 交易对符号，None表示获取所有持仓
            keep_origin: 是否保持原始格式
            instType: 产品类型
            
        Returns:
            tuple: (position_data, error)
        """
        if hasattr(self.aster, "get_position"):
            try:
                success, error = self.aster.get_position(symbol=symbol)
                if keep_origin:
                    return success, error

                if error:
                    return None, error

                # 统一结构：单个持仓对象或列表
                if isinstance(success, dict):
                    # 单个持仓
                    unified = self._normalize_position(success)
                    if symbol and isinstance(unified, dict):
                        # 筛选单个 symbol
                        if str(unified.get('symbol')).upper() == str(symbol).upper():
                            return unified, None
                    return unified, None
                elif isinstance(success, list):
                    # 多个持仓
                    unified = []
                    for pos in success:
                        normalized_pos = self._normalize_position(pos)
                        if normalized_pos:
                            unified.append(normalized_pos)
                    
                    if symbol and isinstance(unified, list):
                        # 筛选单个 symbol
                        for u in unified:
                            if str(u.get('symbol')).upper() == str(symbol).upper():
                                return u, None
                    return unified, None
                else:
                    return success, None
            except Exception as e:
                return None, e
        raise NotImplementedError("aster client lacks get_position")
    
    def _normalize_position(self, pos):
        """
        标准化持仓数据
        
        Args:
            pos: 原始持仓数据
            
        Returns:
            dict: 标准化的持仓数据
        """
        try:
            qty = float(pos.get('quantity') or 0.0)
            side = 'long' if qty > 0 else ('short' if qty < 0 else 'flat')
            entry = float(pos.get('entryPrice') or 0.0)
            mark = float(pos.get('markPrice') or 0.0)
            upl = float(pos.get('pnlUnrealized') or 0.0)
            realized = float(pos.get('pnlRealized') or 0.0)
            lev = float(pos.get('leverage') or 0.0)
            liq = float(pos.get('liquidationPrice') or 0.0) if pos.get('liquidationPrice') not in (None, '') else None
            ts = int(pos.get('ts') or 0)
            quantityUSD = float(pos.get('quantityUSD') or 0)
            fee = float(pos.get('fee') or 0)
            
            return {
                'symbol': pos.get('symbol'),
                'positionId': pos.get('positionId'),
                'side': side,
                'quantity': abs(qty),
                'quantityUSD': abs(quantityUSD),
                'entryPrice': entry,
                'markPrice': mark,
                'pnlUnrealized': upl,
                'pnlRealized': realized,
                'leverage': lev,
                'liquidationPrice': liq,
                'ts': ts,
                'fee': fee,
                'breakEvenPrice': pos.get('breakEvenPrice')
            }
        except Exception as e:
            print(f"标准化持仓数据时发生异常: {str(e)}")
            return None

    def close_all_positions(self, mode="market", price_offset=0.0005, symbol=None, side=None, is_good=None):
        """
        平掉所有仓位，可附加过滤条件（Aster DEX 版）
        
        Args:
            mode: "market" 或 "limit"
            price_offset: limit 平仓时的价格偏移系数（相对 markPx）
            symbol: 仅平某个币种 (e.g. "ETH-USDT")
            side: "long" 仅平多仓, "short" 仅平空仓, None 表示不限
            is_good: True 仅平盈利仓, False 仅平亏损仓, None 表示不限
        """
        # 获取原始仓位数据
        pos_raw, err = self.get_position(symbol=symbol, keep_origin=True)
        if err:
            print("[Aster] get_position error:", err)
            return

        # 处理单个持仓或持仓列表
        if isinstance(pos_raw, dict):
            positions = [pos_raw]
        elif isinstance(pos_raw, list):
            positions = pos_raw
        else:
            positions = []

        if not positions:
            print("✅ 当前无持仓")
            return

        # 归一化 symbol 用于比较
        full_sym = None
        if symbol:
            full_sym, _, _ = self._norm_symbol(symbol)

        for pos in positions:
            try:
                sym = pos.get('symbol')
                qty = float(pos.get('quantity') or 0.0)
                mark_price = float(pos.get('markPrice') or pos.get('markPrice') or 0.0)
                pnl_unreal = float(pos.get('pnlUnrealized') or 0.0)
            except Exception:
                continue

            if qty == 0:
                continue  # 跳过空仓

            # 过滤 symbol
            if full_sym and sym != full_sym:
                continue

            # 判断仓位方向
            pos_side = "long" if qty > 0 else "short"

            # 过滤 side
            if side and side != pos_side:
                continue

            # 过滤 盈亏
            if is_good is True and pnl_unreal <= 0:
                continue
            if is_good is False and pnl_unreal > 0:
                continue

            # 构造平仓单（Aster DEX 下：多仓 -> 卖出，空仓 -> 买入）
            if qty > 0:
                order_side = "sell"
                size = abs(qty)
            else:
                order_side = "buy"
                size = abs(qty)

            if mode == "market":
                try:
                    self.place_order(symbol=sym, side=order_side, order_type="market", size=size)
                    print(f"📤 市价平仓: {sym} {order_side} {size}")
                except Exception as e:
                    print(f"[Aster] 市价平仓失败 {sym}: {e}")
            elif mode == "limit":
                try:
                    if order_side == "sell":
                        price = mark_price * (1 + price_offset)
                    else:
                        price = mark_price * (1 - price_offset)
                    self.place_order(symbol=sym, side=order_side, order_type="limit", size=size, price=price)
                    print(f"📤 限价平仓: {sym} {order_side} {size} @ {price}")
                except Exception as e:
                    print(f"[Aster] 限价平仓失败 {sym}: {e}")
            else:
                raise ValueError("mode 必须是 'market' 或 'limit'")
