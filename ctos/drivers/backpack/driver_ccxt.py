# -*- coding: utf-8 -*-
# ctos/drivers/backpack/driver_ccxt.py
# Backpack driver using ccxt library
# pip install ccxt

from __future__ import print_function

from ast import main
import os
import time
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
import sys
import json

# ccxt connector
try:
    from ccxt import backpack as ccxt_backpack
except ImportError:
    raise RuntimeError("请先安装ccxt: pip install ccxt")

# Import syscall base
try:
    from ctos.core.kernel.syscalls import TradingSyscalls
except ImportError:
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
    from ctos.core.kernel.syscalls import TradingSyscalls

# Import account reader
try:
    from configs.account_reader import get_backpack_credentials, list_accounts
except ImportError:
    # 如果无法导入，使用备用方案
    def get_backpack_credentials(account='main'):
        return {
            'public_key': os.getenv("BP_PUBLIC_KEY", ""),
            'secret_key': os.getenv("BP_SECRET_KEY", "")
        }
    
    def list_accounts(exchange='backpack'):
        return ['main', 'grid', 'rank']  # 默认账户列表

def get_account_name_by_id(account_id=0, exchange='backpack'):
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
            print(f"警告: 账户ID {account_id} 超出范围，使用默认账户 'main'")
            return 'main'
    except Exception as e:
        print(f"获取账户名称失败: {e}，使用默认账户 'main'")
        return 'main'

def init_BackpackClients(window=10000, account_id=0):
    """
    Initialize Backpack ccxt client using account configuration.
    
    Args:
        window: 时间窗口参数
        account_id: 账户ID，根据配置文件中的账户顺序映射 (0=第一个账户, 1=第二个账户, ...)
        
    Returns:
        tuple: (Account, Public) 客户端实例
        
    Note:
        账户ID映射基于configs/account.yaml中accounts.backpack下的账户顺序
        例如: 如果配置文件中有['main', 'grid', 'rank']，则account_id=0对应main，account_id=1对应grid
    """
    # 从配置文件动态获取账户名称
    account_name = get_account_name_by_id(account_id, 'backpack')
    
    try:
        # 使用账户获取器获取认证信息
        credentials = get_backpack_credentials(account_name)
        public_key = credentials.get('public_key', '')
        secret_key = credentials.get('secret_key', '')
        
        if not public_key or not secret_key:
            print(f"[Backpack] 账户 {account_name} (ID: {account_id}) 认证信息不完整")
            print(f"[Backpack] 尝试使用环境变量作为备用方案")
            # 回退到环境变量
            public_key = os.getenv("BP_PUBLIC_KEY", public_key)
            secret_key = os.getenv("BP_SECRET_KEY", secret_key)
            
        if not public_key or not secret_key:
            missing = []
            if not public_key:
                missing.append("BP_PUBLIC_KEY")
            if not secret_key:
                missing.append("BP_SECRET_KEY")
            print(f"[Backpack] Missing credentials for account {account_name}: {', '.join(missing)}")
            return None, None
            
    except Exception as e:
        print(f"[Backpack] 获取账户 {account_name} 认证信息失败: {e}")
        print(f"[Backpack] 尝试使用环境变量作为备用方案")
        # 回退到环境变量
        public_key = os.getenv("BP_PUBLIC_KEY")
        secret_key = os.getenv("BP_SECRET_KEY")
        
        if not public_key or not secret_key:
            missing = []
            if not public_key:
                missing.append("BP_PUBLIC_KEY")
            if not secret_key:
                missing.append("BP_SECRET_KEY")
            print(f"[Backpack] Missing environment vars: {', '.join(missing)}")
            return None
    
    account = None
    try:
        # 使用ccxt创建backpack客户端
        config = {
            'apiKey': public_key,
            'secret': secret_key,
            'sandbox': False,  # 生产环境
            'enableRateLimit': True,
            'proxies': {'https': 'socks5h://127.0.0.1:1080',}

        }
        
        account = ccxt_backpack(config)
        print(f"✓ Backpack CCXT客户端初始化成功 (账户: {account_name}, ID: {account_id})")
    except Exception as e:
        print(f'✗ Backpack CCXT客户端初始化失败: {e}')
        return None
    
    return account


class BackpackDriver(TradingSyscalls):
    """
    CTOS Backpack driver (ccxt connector).
    Mode-aware symbol normalization for Backpack style symbols:
      - spot:  "BASE_QUOTE"           e.g. "SOL_USDC"
      - perp:  "BASE_USDC_PERP"       e.g. "ETH_USDC_PERP"
    Accepts inputs like 'eth-usdc', 'ETH/USDC', 'ETH-USDC-SWAP', 'eth', etc.
    """

    def __init__(self, account_client=None, mode="perp", default_quote="USDC", account_id=0):
        self.cex = 'Backpack'
        self.quote_ccy = 'USDC'
        self.account_id = account_id
        """
        :param account_client: Optional. An initialized ccxt exchange client.
        :param public_client: Optional. An initialized ccxt exchange client.
        :param mode: "perp" or "spot". If "perp", we append '_PERP' suffix when needed.
        :param default_quote: default quote when user passes 'ETH' without '_USDC'
        :param account_id: 账户ID，根据配置文件中的账户顺序映射 (0=第一个账户, 1=第二个账户, ...)
        """
        if account_client is None:
            acc = init_BackpackClients(account_id=account_id)
            self.account = account_client or acc
            if acc:
                print(f"✓ Backpack Driver初始化成功 (账户ID: {account_id})")
            else:
                print(f"✗ Backpack Driver初始化失败 (账户ID: {account_id})")
        else:
            self.account = account_client
            print(f"✓ Backpack Driver使用外部客户端 (账户ID: {account_id})")
        self.mode = (mode or "perp").lower()
        self.default_quote = default_quote or "USDC"
        self.symbol = 'ETH_USDC_PERP'
        self.load_exchange_trade_info()
        self.order_id_to_symbol = {}


    def save_exchange_trade_info(self):
        with open(os.path.dirname(os.path.abspath(__file__)) + '/exchange_trade_info.json', 'w') as f:
            json.dump(self.exchange_trade_info, f)

    def load_exchange_trade_info(self):
        if not os.path.exists(os.path.dirname(os.path.abspath(__file__)) + '/exchange_trade_info.json'):
            self.exchange_trade_info = {}
            return
        with open(os.path.dirname(os.path.abspath(__file__)) + '/exchange_trade_info.json', 'r') as f:
            self.exchange_trade_info = json.load(f)
            # print('load_exchange_trade_info', os.path.dirname(os.path.abspath(__file__)) + '/exchange_trade_info.json')
            # print('load_exchange_trade_info', self.exchange_trade_info)
    # -------------- helpers --------------
    def _norm_symbol(self, symbol):
        """
        Normalize symbols to Backpack format.
        Returns (full_symbol, base_lower, quote_upper)
        Examples:
          _norm_symbol('eth') -> ('ETH_USDC_PERP' if perp else 'ETH_USDC', 'eth', 'USDC')
          _norm_symbol('ETH-USDC-SWAP') -> ('ETH_USDC_PERP', 'eth', 'USDC')
          _norm_symbol('SOL/USDC') -> ('SOL_USDC[_PERP]', 'sol', 'USDC')
          _norm_symbol('BTC_USDC_PERP') -> ('BTC_USDC_PERP', 'btc', 'USDC')
        """
        s = str(symbol or "").strip()
        if not s:
            return None, None, None
            # raise ValueError("symbol is empty")

        # unify separators to underscore and uppercase
        su = s.replace("-", "_").replace("/", "_").upper()

        # Already a full Backpack symbol
        if su.endswith("_PERP") or ("_" in su and not su.endswith("_PERP")):
            parts = su.split("_")
            base = parts[0]
            # try to infer quote when provided
            quote = parts[1] if len(parts) > 1 else self.default_quote
            full = su
        else:
            # Only base provided
            base = su
            quote = self.default_quote
            full = f"{base}_{quote}"

        if self.mode == "perp" and not full.endswith("_PERP"):
            # Backpack perps generally quoted in USDC, enforce quote
            base_only = full.split("_")[0]
            full = f"{base_only}_{self.default_quote}_PERP"
        elif self.mode != "perp" and full.endswith("_PERP"):
            # If spot mode but input is perp, strip suffix
            full = full.replace("_PERP", "")
        if full in ['KSHIB_USDC_PERP', 'KPEPE_USDC_PERP', 'KBONK_USDC_PERP']:
            full = full[0].lower() + full[1:]
        if full in ['SHIB_USDC_PERP', 'PEPE_USDC_PERP', 'BONK_USDC_PERP']:
            full = 'k' + full
        return full, base.lower(), quote.upper()

    def _timeframe_to_seconds(self, timeframe):
        """Parse timeframe like '1m','15m','1h','4h','1d','1w' -> seconds"""
        tf = str(timeframe).strip().lower()
        if tf.endswith('m'):
            return int(tf[:-1]) * 60
        if tf.endswith('h'):
            return int(tf[:-1]) * 60 * 60
        if tf.endswith('d'):
            return int(tf[:-1]) * 24 * 60 * 60
        if tf.endswith('w'):
            return int(tf[:-1]) * 7 * 24 * 60 * 60
        # default try minutes
        try:
            return int(tf) * 60
        except Exception:
            raise ValueError("Unsupported timeframe: %s" % timeframe)

    # -------------- ref-data / meta --------------
    def symbols(self, instType='PERP'):
        """
        返回指定类型的交易对列表。
        :param instType: 'PERP' | 'SPOT' | 'MARGIN' 等，默认 'PERP'
        :return: list[str]，如 ['BTC_USDC_PERP', 'ETH_USDC_PERP', ...]
        """
        if not hasattr(self, "account") or self.account is None:
            # 兜底：无法从底层获取时，返回少量默认
            return ["BTC_USDC_PERP", "ETH_USDC_PERP", "SOL_USDC_PERP"] if str(instType).upper() == 'PERP' else ["BTC_USDC", "ETH_USDC", "SOL_USDC"]
        try:
            markets = self.account.load_markets()
            if self.mode == "perp":
                # 永续合约市场
                syms = [symbol for symbol, market in markets.items() 
                       if market.get('type') == 'future' and market.get('active', True)]
            else:
                # 现货市场
                syms = [symbol for symbol, market in markets.items() 
                       if market.get('type') == 'spot' and market.get('active', True)]
            return syms, None
        except Exception as e:
            return None, e

    def exchange_limits(self, symbol=None, instType='PERP'):
        """
        获取交易所限制信息，包括价格精度、数量精度、最小下单数量等
        
        :param symbol: 交易对符号，如 'ETH_USDC_PERP'，如果为None则返回全类型数据
        :param instType: 产品类型，默认为 'PERP'
        :return: dict 包含限制信息的字典
        """
        if symbol:
            symbol, _, _ = self._norm_symbol(symbol)
            if symbol in self.exchange_trade_info:
                return self.exchange_trade_info[symbol], None
        try:
            markets = self.account.load_markets()
            
            # 如果指定了symbol，获取单个交易对信息
            if symbol:
                if symbol not in markets:
                    return {"error": f"未找到交易对 {symbol} 的信息"}, None
                
                market = markets[symbol]
                limits = self._extract_limits_from_market(market)
                if limits and 'error' not in limits:
                    self.exchange_trade_info[symbol] = limits
                    self.save_exchange_trade_info()
                return limits, None
            
            # 如果没有指定symbol，获取所有交易对信息
            result = []
            for symbol_name, market in markets.items():
                if self.mode == "perp" and market.get('type') != 'future':
                    continue
                if self.mode == "spot" and market.get('type') != 'spot':
                    continue
                    
                limits = self._extract_limits_from_market(market)
                if limits and 'error' not in limits:
                    result.append(limits)
                    self.exchange_trade_info[symbol_name] = limits
            
            self.save_exchange_trade_info()
            return result, None
            
        except Exception as e:
            return None, {"error": f"处理数据时发生异常: {str(e)}"}
    
    def _extract_limits_from_market(self, market):
        """
        从ccxt market信息中提取限制信息
        
        :param market: ccxt market信息字典
        :return: dict 包含限制信息的字典
        """
        try:
            symbol = market.get('symbol', '')
            
            # 从ccxt market信息中提取精度和限制
            price_precision = market.get('precision', {}).get('price', 0.01)
            size_precision = market.get('precision', {}).get('amount', 0.001)
            min_qty = market.get('limits', {}).get('amount', {}).get('min', 0.001)
            
            return {
                'symbol': symbol,
                'instType': 'PERP' if self.mode == 'perp' else 'SPOT',
                'price_precision': price_precision,
                'size_precision': size_precision,
                'min_order_size': min_qty,
                'contract_value': 1.0,
                'max_leverage': 125.0 if self.mode == 'perp' else 1.0,
                'state': 'live' if market.get('active', True) else 'inactive',
                'raw': market
            }
        except Exception as e:
            return {"error": f"解析market信息时发生异常: {str(e)}"}

    def fees(self, symbol='ETH_USDC_PERP', instType='PERP', keep_origin=False, limit=3, offset=0):
        """
        获取资金费率信息。
        - 对于 Backpack，使用 fetch_funding_rate() 方法
        - 返回 (result, error)
        - 统一返回结构到"每小时资金费率"。
        """
        if not hasattr(self.account, 'fetch_funding_rate'):
            return None, NotImplementedError('account.fetch_funding_rate unavailable')

        full, _, _ = self._norm_symbol(symbol)
        if self.mode != "perp":
            return {"symbol": full, "instType": "SPOT", "fundingRate_hourly": None, "raw": None}, None
        
        try:
            raw = self.account.fetch_funding_rate(symbol=full)
            if keep_origin:
                return raw, None
            
            # ccxt返回格式: {'symbol': 'ETH_USDC_PERP', 'fundingRate': 0.0001, 'timestamp': 1692345600000, 'datetime': '2023-08-17T00:00:00.000Z'}
            fr_period = raw.get('fundingRate')
            ts_ms = raw.get('timestamp')
            period_hours = 8.0  # Backpack默认8小时周期

            hourly = None
            if fr_period is not None:
                hourly = fr_period / period_hours

            result = {
                'symbol': full,
                'instType': instType,
                'fundingRate_hourly': hourly,
                'fundingRate_period': fr_period,
                'period_hours': period_hours,
                'fundingTime': ts_ms,
                'raw': raw,
                'latest': raw,
            }
            return result, None
        except Exception as e:
            return None, e

    # -------------- market data --------------
    def get_price_now(self, symbol='ETH_USDC_PERP'):
        full, base, _ = self._norm_symbol(symbol)
        if hasattr(self.account, "fetch_ticker"):
            try:
                data = self.account.fetch_ticker(symbol=full)
                # ccxt返回格式: {'symbol': 'ETH_USDC_PERP', 'last': 2000.0, 'bid': 1999.0, 'ask': 2001.0, ...}
                if isinstance(data, dict):
                    price = data.get('last') or data.get('close')
                    if price is not None:
                        return float(price), None
            except Exception as e:
                return None, e
        return None, NotImplementedError("account.fetch_ticker unavailable or response lacks price")

    def get_orderbook(self, symbol='ETH_USDC_PERP', level=50):
        full, _, _ = self._norm_symbol(symbol)
        if hasattr(self.account, "fetch_order_book"):
            try:
                raw = self.account.fetch_order_book(symbol=full, limit=int(level))
                bids = raw.get("bids", []) if isinstance(raw, dict) else []
                asks = raw.get("asks", []) if isinstance(raw, dict) else []
                return {"symbol": full, "bids": bids, "asks": asks}, None
            except Exception as e:
                return None, e
        return None, NotImplementedError("account.fetch_order_book unavailable")

    def get_klines(self, symbol='ETH_USDC', timeframe='1m', limit=200, start_time=None, end_time=None):
        full, _, _ = self._norm_symbol(symbol)
        if not hasattr(self.account, "fetch_ohlcv"):
            return None, NotImplementedError("account.fetch_ohlcv unavailable")

        # 计算缺省时间范围：对齐到周期边界，起点=对齐后的边界-(limit-1)*tf，终点=当前时间
        try:
            tf_seconds = self._timeframe_to_seconds(timeframe)
        except Exception as e:
            return None, e

        now_sec = int(time.time())
        if end_time is None:
            end_time = now_sec
        if start_time is None:
            aligned_end_boundary = end_time - (end_time % tf_seconds)
            start_time = aligned_end_boundary - (int(limit) - 1) * tf_seconds

        # 拉取原始数据
        try:
            since = int(start_time * 1000) if start_time else None
            raw = self.account.fetch_ohlcv(symbol=full, timeframe=timeframe, since=since, limit=int(limit))
        except Exception as e:
            return None, e

        # 统一为列表
        if isinstance(raw, list):
            rows = raw
        else:
            return None, ValueError("Unexpected ohlcv response format")

        # 重排为目标DF格式: trade_date(ms), open, high, low, close, vol1(base), vol(quote)
        records = []
        for k in rows:
            if not isinstance(k, list) or len(k) < 6:
                continue
            try:
                # ccxt ohlcv row: [timestamp, open, high, low, close, volume]
                ts_ms = int(k[0])  # 时间戳（毫秒）
                o = float(k[1])
                h = float(k[2])
                l = float(k[3])
                c = float(k[4])
                base_vol = float(k[5])
                quote_vol = base_vol * c  # 估算quote volume

                records.append({
                    'trade_date': ts_ms,
                    'open': o,
                    'high': h,
                    'low': l,
                    'close': c,
                    'vol1': base_vol,
                    'vol': quote_vol,
                })
            except Exception:
                # 跳过坏行
                continue

        # 时间升序并裁剪到 limit
        records.sort(key=lambda r: r['trade_date'])
        if limit and len(records) > int(limit):
            records = records[-int(limit):]

        # 优先返回 pandas.DataFrame
        try:
            import pandas as pd
            df = pd.DataFrame.from_records(records, columns=['trade_date', 'open', 'high', 'low', 'close', 'vol1', 'vol'])
            return df, None
        except Exception:
            # 退化为列表
            return records, None

    # -------------- trading --------------
    def place_order(self, symbol, side, order_type, size, price=None, client_id=None, max_retries=4, **kwargs):
        """
        下单函数，带错误处理和重试机制
        
        自动处理以下错误类型：
        - Price precision error: 自动调整价格精度
        - Quantity precision error: 自动调整数量精度  
        - Quantity below minimum: 自动增加数量到最小允许值
        - Invalid symbol: 自动调整符号格式
        
        使用示例：
        >>> driver = BackpackDriver()
        >>> # 正常下单
        >>> order_id, error = driver.place_order('ETH_USDC_PERP', 'buy', 'limit', 0.01, 2000.0)
        >>> # 带重试的下单
        >>> order_id, error = driver.place_order('ETH_USDC_PERP', 'buy', 'limit', 0.01, 2000.0, max_retries=5)
        
        :param symbol: 交易对
        :param side: 买卖方向 ('buy'/'sell')
        :param order_type: 订单类型 ('limit'/'market')
        :param size: 数量
        :param price: 价格（限价单需要）
        :param client_id: 客户端订单ID
        :param max_retries: 最大重试次数
        :param kwargs: 其他参数
        :return: (order_id, error)
        """
        full, _, _ = self._norm_symbol(symbol)
        if not hasattr(self.account, "create_order"):
            return None, NotImplementedError("Account.create_order unavailable")

        original_size = size
        original_price = price
        
        for attempt in range(max_retries + 1):
            try:
                # Map CTOS -> ccxt format
                ccxt_side = "buy" if str(side).lower() in ("buy", "bid", "long") else "sell"
                ccxt_type = "limit" if str(order_type).lower() in ("limit",) else "market"
                
                params = {
                    "symbol": full,
                    "side": ccxt_side,
                    "type": ccxt_type,
                    "amount": float(size),
                }
                if price is not None:
                    params["price"] = float(price)
                if client_id:
                    params["clientOrderId"] = client_id
                # passthrough extras like post_only
                params.update(kwargs)

                order = self.account.create_order(**params)
                
                # 检查下单结果
                if isinstance(order, dict) and ('id' in order or 'orderId' in order):
                    # 下单成功
                    order_id = order.get('id') or order.get('orderId')
                    if attempt > 0:
                        print(f"✓ 下单成功 (重试第{attempt}次): {symbol} {side} {size}@{price}")
                    return str(order_id), None
                else:
                    # 下单失败，检查是否有重试机会
                    if attempt < max_retries:
                        error_msg = str(order) if order else "Unknown error"
                        print(f"⚠ 下单失败 (第{attempt + 1}次): {error_msg}")
                        
                        # 根据错误类型进行相应的调整
                        error_lower = error_msg.lower()
                        
                        # 记录调整前的参数
                        original_price = price
                        original_size = size
                        
                        # 判断错误类型并调整参数
                        if 'precision' in error_lower and 'price' in error_lower:
                            # 价格精度问题，调整价格精度
                            if order_type.lower() == 'limit' and price is not None:
                                price = round(float(price), 4)
                                print(f"🔧 调整价格精度: {original_price} -> {price}")
                                
                        elif 'precision' in error_lower and 'quantity' in error_lower:
                            # 数量精度问题，调整数量精度
                            size = round(float(size), 4)
                            print(f"🔧 调整数量精度: {original_size} -> {size}")
                            
                        elif 'min notional' in error_lower or 'below minimum' in error_lower:
                            # 数量过小，增加数量
                            size = max(size * 1.1, 0.001)
                            print(f"🔧 增加数量: {original_size} -> {size}")
                            
                        elif 'invalid symbol' in error_lower:
                            # 符号无效，尝试重新规范化
                            full, _, _ = self._norm_symbol(symbol)
                            print(f"🔧 重新规范化符号: {symbol} -> {full}")
                            
                        else:
                            # 未知错误类型，尝试通用调整策略
                            print(f"⚠ 未知错误类型，尝试通用调整: {error_msg}")
                            if order_type.lower() == 'limit' and price is not None:
                                # 尝试减少价格精度
                                price = round(float(price), 4)
                                print(f"🔧 通用调整价格精度: {original_price} -> {price}")
                            
                            # 尝试减少数量精度
                            size = round(float(size), 4)
                            print(f"🔧 通用调整数量精度: {original_size} -> {size}")
                        
                        # 等待一段时间后重试
                        time.sleep(0.5)
                    else:
                        # 最后一次尝试失败，返回错误
                        print(f"✗ 下单最终失败: {symbol} {side} {size}@{price}")
                        return None, order
                        
            except Exception as e:
                if attempt < max_retries:
                    print(f"⚠ 下单异常 (第{attempt + 1}次): {str(e)}")
                    time.sleep(0.5)
                else:
                    print(f"✗ 下单异常最终失败: {str(e)}")
                    return None, str(e)
        
        return None, "Max retries exceeded"

    def amend_order(self, order_id, symbol, price=None, size=None, side=None, order_type=None,
                    time_in_force=None, post_only=None, **kwargs):
        """
        通过 查单->撤单->下单 组合实现改单。
        - symbol 必填（撤单需要）
        - 未提供的新参数将继承原订单（side/type/price/size/timeInForce/postOnly）
        - 支持只改价、只改量、同时修改、以及更改 tif/post_only

        返回: (new_order_id_or_obj, error)
        """
        if not order_id:
            return None, ValueError("order_id is required")
        if not symbol:
            return None, ValueError("symbol is required")

        full, _, _ = self._norm_symbol(symbol)

        # 1) 查单
        existing_order = None
        try:
            od, oerr = self.get_order_status(order_id=order_id, symbol=full, keep_origin=True)
            if oerr is None and od.get('orderId', None) == order_id:
                existing_order = od
            else:
                return None, None
        except Exception:
            existing_order = None
            return None, None
        # 2) 撤单
        ok, cerr = self.revoke_order(order_id, symbol=full)
        if not ok:
            return None, cerr or RuntimeError("cancel order failed")

        # 3) 组装新单参数：优先用传入，其次用旧单
        def _get(o, keys, default=None):
            if not isinstance(o, dict):
                return default
            for k in keys:
                v = o.get(k)
                if v is not None:
                    return v
            return default

        old_side = _get(existing_order, ['side', 'orderSide'])
        old_type = _get(existing_order, ['type', 'orderType'])
        old_qty = _get(existing_order, ['origQty', 'quantity', 'size', 'qty'])
        old_price = _get(existing_order, ['price'])

        new_side = side if side is not None else old_side
        new_type = order_type if order_type is not None else old_type
        new_qty = size if size is not None else old_qty
        new_price = price if price is not None else old_price

        if not new_side:
            return None, ValueError("side not provided and cannot infer from existing order")
        if not new_type:
            new_type = 'LIMIT' if new_price is not None else 'MARKET'
        if not new_qty:
            return None, ValueError("size not provided and cannot infer from existing order")

        return self.place_order(
            symbol=full,
            side=new_side,
            order_type=new_type,
            size=str(new_qty),
            price=str(new_price) if new_price is not None else None,
            **kwargs
        )

    def revoke_order(self, order_id, symbol=None):
        if hasattr(self.account, "cancel_order"):
            if not symbol:
                return False, ValueError("symbol is required for cancel_order on Backpack")
            full, _, _ = self._norm_symbol(symbol)
            try:
                resp = self.account.cancel_order(symbol=full, id=order_id)
                return True, None if resp is not None else (False, resp)
            except Exception as e:
                return False, e
        return False, NotImplementedError("Account.cancel_order unavailable")

    def get_order_status(self, order_id=None, symbol='ETH_USDC_PERP', market_type=None, window=None, keep_origin=False):
        full, _, _ = self._norm_symbol(symbol)
        if not hasattr(self.account, "fetch_order"):
            return None, NotImplementedError("Account.fetch_order unavailable")
        try:
            resp = self.account.fetch_order(id=order_id, symbol=full)
            if keep_origin:
                if order_id is None:
                    return resp, None
                # 过滤指定 order_id
                if isinstance(resp, dict):
                    if str(resp.get('orderId')) == str(order_id):
                        return resp, None
                    return None, None
                if isinstance(resp, list):
                    for od in resp:
                        try:
                            if str(od.get('orderId')) == str(order_id):
                                return od, None
                        except Exception:
                            continue
                    return None, None
                return None, None

            # 统一结构
            od = None
            if isinstance(resp, dict):
                od = resp
            elif isinstance(resp, list):
                for item in resp:
                    try:
                        if str(item.get('orderId')) == str(order_id):
                            od = item
                            break
                    except Exception:
                        continue
            if not od:
                return None, None

            def _f(v, cast=float):
                try:
                    return cast(v)
                except Exception:
                    return None

            normalized = {
                'orderId': od.get('orderId') or od.get('ordId'),
                'symbol': od.get('symbol') or od.get('market') or od.get('instId'),
                'side': (od.get('side') or '').lower() if od.get('side') else None,
                'orderType': (od.get('type') or '').lower() if (od.get('type')) else None,
                'price': _f(od.get('price')),
                'quantity': _f(od.get('origQty')),
                'filledQuantity': _f(od.get('executedQty')),
                'status': od.get('status'),
                'timeInForce': od.get('timeInForce') or od.get('time_in_force'),
                'postOnly': od.get('postOnly') or od.get('post_only'),
                'reduceOnly': od.get('reduceOnly') or od.get('reduce_only'),
                'clientId': od.get('clientOrderId') or od.get('client_id'),
                'createdAt': _f(od.get('time'), int),
                'updatedAt': _f(od.get('updateTime'), int),
                'raw': od,
            }
            return normalized, None
        except Exception as e:
            return None, e

    def get_open_orders(self, symbol=None, instType='PERP', onlyOrderId=True, keep_origin=True):
        """
        获取未完成订单列表。
        :param symbol: 指定交易对；为空则返回全部（若底层支持）
        :param instType: 市场类型，默认 'PERP'
        :param onlyOrderId: True 则仅返回订单号列表；False 返回完整订单对象列表
        :return: (result, error)
        """
        if hasattr(self.account, "fetch_open_orders"):
            try:
                if symbol:
                    try:
                        full, _, _ = self._norm_symbol(symbol)
                    except Exception as e:
                        full = symbol
                else:
                    full = symbol
                resp = self.account.fetch_open_orders(symbol=full)

                if onlyOrderId:
                    order_ids = []
                    # 兼容 list / dict 两种返回结构
                    if isinstance(resp, list):
                        for od in resp:
                            try:
                                oid = od.get('orderId') if isinstance(od, dict) else None
                                if oid is not None:
                                    order_ids.append(str(oid))
                            except Exception:
                                continue
                    elif isinstance(resp, dict):
                        data = resp.get('data')
                        if isinstance(data, list):
                            for od in data:
                                try:
                                    oid = od.get('orderId') if isinstance(od, dict) else None
                                    if oid is not None:
                                        order_ids.append(str(oid))
                                except Exception:
                                    continue
                        else:
                            # 单个订单或以键为订单号等情况
                            oid = resp.get('orderId')
                            if oid is not None:
                                order_ids.append(str(oid))
                    return order_ids, None

                if keep_origin:
                    return resp, None

                # 统一结构输出 list[dict]
                def to_norm(od):
                    if not isinstance(od, dict):
                        return None
                    def _f(v, cast=float):
                        try:
                            return cast(v)
                        except Exception:
                            return None
                    return {
                        'orderId': od.get('orderId') or od.get('ordId'),
                        'symbol': od.get('symbol') or od.get('market') or od.get('instId'),
                        'side': (od.get('side') or '').lower() if od.get('side') else None,
                        'orderType': (od.get('type') or '').lower() if (od.get('type')) else None,
                        'price': _f(od.get('price')),  # str -> float
                        'quantity': _f(od.get('origQty')),  # str -> float
                        'filledQuantity': _f(od.get('executedQty')),  # str -> float
                        'status': od.get('status'),
                        'timeInForce': od.get('timeInForce') or od.get('time_in_force'),
                        'postOnly': od.get('postOnly') or od.get('post_only'),
                        'reduceOnly': od.get('reduceOnly') or od.get('reduce_only'),
                        'clientId': od.get('clientOrderId') or od.get('client_id'),
                        'createdAt': _f(od.get('time'), int),
                        'updatedAt': _f(od.get('updateTime'), int),
                        'raw': od,
                    }

                normalized = []
                if isinstance(resp, list):
                    for od in resp:
                        n = to_norm(od)
                        if n:
                            normalized.append(n)
                elif isinstance(resp, dict):
                    data = resp.get('data')
                    if isinstance(data, list):
                        for od in data:
                            n = to_norm(od)
                            if n:
                                normalized.append(n)
                    else:
                        n = to_norm(resp)
                        if n:
                            normalized.append(n)
                return normalized, None
            except Exception as e:
                return None, e
        else:
            return None, Exception("Account client not available")

    def cancel_all(self, symbol='ETH_USDC_PERP', order_ids=[]):
        """
        撤销指定交易对的所有未完成订单。
        :param symbol: 交易对；为空则撤销全部（若底层支持）
        :param order_ids: 若提供，则仅撤销这些订单号（若底层支持）
        :return: (result, error)
        """
        if hasattr(self.account, "cancel_all_orders"):
            try:
                if symbol:
                    try:
                        full, _, _ = self._norm_symbol(symbol)
                    except Exception as e:
                        full = symbol
                else:
                    full = symbol
                resp = self.account.cancel_all_orders(symbol=full)
                return resp, None
            except Exception as e:
                return None, e
        else:
            return None, Exception("Account client not available")

    # -------------- account --------------
    def fetch_balance(self, currency='USDC', window=1):
        """
        获取账户余额。
        :param currency: 币种，默认 'USDC'
        :param window: 时间窗口参数（保持兼容性）
        :return: (balance, error)
        """
        if hasattr(self.account, "fetch_balance"):
            try:
                cur = (currency or "").upper()
                balance = self.account.fetch_balance()
                
                if cur in balance:
                    # 返回可用余额
                    return float(balance[cur].get('free', 0)), None
                return 0.0, None
            except Exception as e:
                return None, e
        else:
            return None, Exception("Account client not available")

    def get_position(self, symbol=None, window=None, keep_origin=False, instType='PERP'):
        """
        获取持仓信息。
        :param symbol: 交易对；为空则返回全部
        :param window: 时间窗口参数（保持兼容性）
        :param keep_origin: True 则返回原始结构；False 则返回统一结构
        :param instType: 市场类型，默认 'PERP'
        :return: (result, error)
        """
        if self.mode == "spot":
            return [], None

        try:
            if hasattr(self.account, "fetch_positions"):
                positions = self.account.fetch_positions(symbols=[symbol] if symbol else None)
            else:
                return [], None
                
            if keep_origin:
                return positions, None
                
            out = []
            for p in positions or []:
                try:
                    qty = float(p.get("contracts") or 0.0)
                except Exception:
                    qty = 0.0
                side = "long" if qty > 0 else ("short" if qty < 0 else "flat")
                def _f(k):
                    try:
                        return float(p.get(k))
                    except Exception:
                        return None
                out.append({
                    "symbol": p.get("symbol"),
                    "positionId": None,
                    "side": side,
                    "quantity": abs(qty),
                    "entryPrice": _f("entryPrice"),
                    "markPrice": _f("markPrice"),
                    "pnlUnrealized": _f("unrealizedPnl"),
                    "pnlRealized": None,
                    "leverage": _f("leverage"),
                    "liquidationPrice": _f("liquidationPrice"),
                    "ts": None,
                })
            if symbol:
                for u in out:
                    if u["symbol"] == self._norm_symbol(symbol)[0]:
                        return u, None
            return out, None
        except Exception as e:
            return None, e

    def close_all_positions(self, mode="market", price_offset=0.0005, symbol=None, side=None, is_good=None, ignore=[], target=[]):
        """
        平仓所有持仓（仅限期货）
        :param mode: 平仓模式，默认 "market"
        :param price_offset: 价格偏移，默认 0.0005
        :param symbol: 交易对；为空则平仓全部
        :param side: 平仓方向，默认 None（平仓所有方向）
        :param is_good: 是否只平仓盈利持仓，默认 None
        :param ignore: 忽略的交易对列表，默认 []
        :param target: 目标交易对列表，默认 []
        :return: (result, error)
        """
        if self.mode == "spot":
            return {"ok": True, "message": "现货无持仓"}, None
        try:
            if hasattr(self.account, "fetch_positions"):
                positions = self.account.fetch_positions(symbols=[symbol] if symbol else None)
            else:
                return {"ok": False, "error": "fetch_positions not available"}, None
                
            for pos in positions or []:
                qty = float(pos.get("contracts", 0))
                if qty != 0:
                    # 平仓
                    side = "sell" if qty > 0 else "buy"
                    try:
                        self.account.create_order(
                            symbol=pos.get("symbol"),
                            side=side,
                            type="market",
                            amount=abs(qty)
                        )
                    except Exception as e:
                        print(f"平仓失败 {pos.get('symbol')}: {e}")
                        
            return {"ok": True}, None
        except Exception as e:
            return {"ok": False, "error": str(e)}, e


def test_backpack_ccxt_driver():
    """测试ccxt版本的Backpack driver"""
    
    print("=== 测试基于ccxt的Backpack Driver ===\n")
    
    try:
        from ctos.drivers.backpack.driver_ccxt import BackpackDriver
        
        # 测试初始化
        print("1. 测试初始化...")
        driver = BackpackDriver(mode="perp", account_id=0)
        print(f"   ✅ 初始化成功: mode={driver.mode}, account_id={driver.account_id}")
        
        # 测试符号标准化
        print("\n2. 测试符号标准化...")
        test_symbols = ["ETH_USDC_PERP", "BTC_USDC_PERP", "eth", "btc", "ETH/USDC", "SOL-USDC-SWAP"]
        for symbol in test_symbols:
            try:
                normalized = driver._norm_symbol(symbol)
                print(f"   ✅ {symbol} -> {normalized}")
            except Exception as e:
                print(f"   ❌ {symbol} -> 错误: {e}")
        
        # 测试时间框架转换
        print("\n3. 测试时间框架转换...")
        test_timeframes = ["1m", "5m", "1h", "4h", "1d", "1w"]
        for tf in test_timeframes:
            try:
                seconds = driver._timeframe_to_seconds(tf)
                print(f"   ✅ {tf} -> {seconds}秒")
            except Exception as e:
                print(f"   ❌ {tf} -> 错误: {e}")
        
        # 测试方法签名
        print("\n4. 测试方法签名...")
        import inspect
        
        methods_to_test = [
            'symbols', 'exchange_limits', 'fees', 'get_price_now',
            'get_orderbook', 'get_klines', 'place_order', 'amend_order',
            'revoke_order', 'get_order_status', 'get_open_orders',
            'cancel_all', 'fetch_balance', 'get_position', 'close_all_positions'
        ]
        
        for method_name in methods_to_test:
            if hasattr(driver, method_name):
                try:
                    sig = inspect.signature(getattr(driver, method_name))
                    params = list(sig.parameters.keys())
                    print(f"   ✅ {method_name}({', '.join(params)})")
                except Exception as e:
                    print(f"   ❌ {method_name}: 无法获取签名 - {e}")
            else:
                print(f"   ❌ {method_name}: 方法不存在")
        
        # 测试Backpack特有功能
        print("\n5. 测试Backpack特有功能...")
        
        # 测试perp模式下的符号处理
        perp_driver = BackpackDriver(mode="perp", account_id=0)
        spot_driver = BackpackDriver(mode="spot", account_id=0)
        
        test_symbol = "ETH-USDC"
        perp_result = perp_driver._norm_symbol(test_symbol)
        spot_result = spot_driver._norm_symbol(test_symbol)
        
        print(f"   ✅ Perp模式 {test_symbol} -> {perp_result}")
        print(f"   ✅ Spot模式 {test_symbol} -> {spot_result}")
        
        # 测试特殊符号处理
        special_symbols = ["SHIB_USDC_PERP", "PEPE_USDC_PERP", "BONK_USDC_PERP"]
        for sym in special_symbols:
            result = perp_driver._norm_symbol(sym)
            print(f"   ✅ 特殊符号 {sym} -> {result}")
        
        print(f"\n=== 测试完成 ===")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_backpack_ccxt_driver()
