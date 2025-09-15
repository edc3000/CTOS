from bpx.account import Account
from bpx.public import Public
import os
import json
from decimal import Decimal, ROUND_DOWN, ROUND_UP
import time

from bpx.constants.enums import OrderTypeType

public_key = os.getenv("BP_PUBLIC_KEY")
secret_key = os.getenv("BP_SECRET_KEY")


def account_client():
    return Account(public_key, secret_key, window=10000)

def public_client():
    return Public()

account = account_client()
account_client = account
public = public_client()

# 精度配置文件路径
PRECISION_CONFIG_FILE = "/home/zzb/Quantify/ctos/ctos/drivers/backpack/precision_config.json"

def load_precision_config():
    """加载精度配置"""
    try:
        if os.path.exists(PRECISION_CONFIG_FILE):
            with open(PRECISION_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"加载精度配置失败: {e}")
        return {}

def save_precision_config(config):
    """保存精度配置"""
    try:
        with open(PRECISION_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"精度配置已保存到: {PRECISION_CONFIG_FILE}")
    except Exception as e:
        print(f"保存精度配置失败: {e}")

def test_price_precision(symbol, current_price, test_quantity=1.0):
    """
    测试价格精度
    返回: (price_precision, test_orders)
    """
    print(f"  测试 {symbol} 价格精度...")
    test_orders = []
    
    # 从0位小数开始测试
    for decimal_places in range(0, 10):  # 最多测试到7位小数
        try:
            # 使用当前价格的95%作为测试价格
            test_price = current_price * 0.95
            
            # 格式化价格到指定小数位数
            if decimal_places == 0:
                formatted_price = str(int(test_price))
            else:
                formatted_price = f"{test_price:.{decimal_places}f}"
            
            # 格式化数量
            formatted_quantity = format_quantity(test_quantity)
            
            print(f"    测试价格精度 {decimal_places} 位: {formatted_price}, 数量: {formatted_quantity}")
            
            # 尝试下单
            order = account.execute_order(
                symbol=symbol,
                side="Bid",
                order_type="Limit",
                quantity=formatted_quantity,
                price=formatted_price,
                time_in_force="GTC",
                post_only=True
            )
            
            if order and isinstance(order, dict) and 'id' in order:
                # 下单成功，记录订单ID用于后续撤单
                test_orders.append(order['id'])
                print(f"    ✓ 价格精度 {decimal_places} 位测试成功")
            else:
                # 下单失败，说明精度过高
                print(f"    ✗ 价格精度 {decimal_places} 位测试失败: {order}")
                return decimal_places - 1, test_orders
                
        except Exception as e:
            print(f"    ✗ 价格精度 {decimal_places} 位测试异常: {e}")
            return decimal_places - 1, test_orders
    
    return 7, test_orders  # 如果都成功，返回最大精度

def test_quantity_precision(symbol, current_price, test_price=None):
    """
    测试数量精度
    返回: (quantity_precision, test_orders)
    """
    print(f"  测试 {symbol} 数量精度...")
    test_orders = []
    
    if test_price is None:
        test_price = current_price * 0.95
    
    # 根据价格计算合适的测试数量
    base_quantity = 20 / current_price
    test_quantity = max(0.00001, base_quantity)  # 确保最小数量
    
    # 获取当前价格的精度（通过字符串判断）
    current_price_str = str(current_price)
    if '.' in current_price_str:
        price_decimal_places = len(current_price_str.split('.')[1])
    else:
        price_decimal_places = 0
    
    # 格式化价格到当前价格的精度
    if price_decimal_places == 0:
        formatted_price = str(int(test_price))
    else:
        formatted_price = f"{test_price:.{price_decimal_places}f}"
    
    # 从0位小数开始测试数量精度
    for decimal_places in range(0, 8):  # 最多测试到7位小数
        try:
            # 格式化数量到指定小数位数
            if decimal_places == 0:
                formatted_quantity = str(int(test_quantity))
            else:
                formatted_quantity = f"{test_quantity:.{decimal_places}f}"
            
            print(f"    测试数量精度 {decimal_places} 位: 价格={formatted_price}, 数量={formatted_quantity}")
            
            # 尝试下单
            order = account.execute_order(
                symbol=symbol,
                side="Bid",
                order_type="Limit",
                quantity=formatted_quantity,
                price=formatted_price,
                time_in_force="GTC",
                post_only=True
            )
            
            if order and isinstance(order, dict) and 'id' in order:
                # 下单成功，记录订单ID用于后续撤单
                test_orders.append(order['id'])
                print(f"    ✓ 数量精度 {decimal_places} 位测试成功")
            else:
                # 下单失败，说明精度过高
                print(f"    ✗ 数量精度 {decimal_places} 位测试失败: {order}")
                return decimal_places - 1, test_orders
                
        except Exception as e:
            print(f"    ✗ 数量精度 {decimal_places} 位测试异常: {e}")
            return decimal_places - 1, test_orders
    
    return 7, test_orders  # 如果都成功，返回最大精度

def cancel_test_orders(symbol, order_ids):
    """撤销测试订单"""
    if not order_ids:
        return
    
    print(f"  撤销 {len(order_ids)} 个测试订单...")
    for order_id in order_ids:
        try:
            result = account.cancel_order(symbol, order_id=order_id)
            print(f"    订单 {order_id} 撤销结果: {result}")
        except Exception as e:
            print(f"    订单 {order_id} 撤销失败: {e}")
        time.sleep(0.1)  # 避免请求过于频繁

def get_symbol_precision(symbol, current_price):
    """
    获取指定交易对的精度配置
    如果配置文件中没有，则通过测试获取
    """
    config = load_precision_config()
    
    if symbol in config:
        print(f"  从配置文件获取 {symbol} 精度: 价格{config[symbol]['price_precision']}位, 数量{config[symbol]['quantity_precision']}位")
        return config[symbol]['price_precision'], config[symbol]['quantity_precision']
    
    print(f"  配置文件中未找到 {symbol} 精度，开始测试...")
    
    # 测试价格精度
    price_precision, price_orders = test_price_precision(symbol, current_price)
    
    # 测试数量精度
    quantity_precision, quantity_orders = test_quantity_precision(symbol, current_price)
    
    # 撤销所有测试订单
    all_orders = price_orders + quantity_orders
    cancel_test_orders(symbol, all_orders)
    
    # 保存精度配置
    config[symbol] = {
        'price_precision': price_precision,
        'quantity_precision': quantity_precision
    }
    save_precision_config(config)
    
    print(f"  {symbol} 精度测试完成: 价格{price_precision}位, 数量{quantity_precision}位")
    return price_precision, quantity_precision


def format_price_with_precision(price, symbol, current_price):
    """
    使用动态精度格式化价格
    """
    try:
        price_precision, _ = get_symbol_precision(symbol, current_price)
        
        # 如果精度为-1，表示需要测试，使用当前价格的精度作为参考
        if price_precision == -1:
            current_price_str = str(current_price)
            if '.' in current_price_str:
                price_precision = len(current_price_str.split('.')[1])
            else:
                price_precision = 0
        
        # 转换为Decimal进行精确计算
        price_decimal = Decimal(str(price))
        
        # 使用测试得到的精度
        if price_precision == 0:
            formatted_price = str(int(price_decimal))
        else:
            formatted_price = f"{price_decimal:.{price_precision}f}"
        
        return formatted_price
    except Exception as e:
        print(f"价格格式化错误: {e}, 原始价格: {price}")
        # 如果格式化失败，使用简单的字符串截断
        price_str = str(price)
        if '.' in price_str:
            integer_part, decimal_part = price_str.split('.', 1)
            if len(decimal_part) > 4:
                decimal_part = decimal_part[:4]
            return f"{integer_part}.{decimal_part}"
        return price_str


def format_quantity_with_precision(quantity, symbol, current_price):
    """
    使用动态精度格式化数量
    """
    try:
        _, quantity_precision = get_symbol_precision(symbol, current_price)
        
        # 如果精度为-1，表示需要测试，使用当前价格的精度作为参考
        if quantity_precision == -1:
            current_price_str = str(current_price)
            if '.' in current_price_str:
                quantity_precision = len(current_price_str.split('.')[1])
            else:
                quantity_precision = 0
        
        # 转换为Decimal进行精确计算
        quantity_decimal = Decimal(str(quantity))
        
        # 使用测试得到的精度
        if quantity_precision == 0:
            formatted_quantity = str(int(quantity_decimal))
        else:
            formatted_quantity = f"{quantity_decimal:.{quantity_precision}f}"
        
        return formatted_quantity
    except Exception as e:
        print(f"数量格式化错误: {e}, 原始数量: {quantity}")
        # 如果格式化失败，使用简单的字符串截断
        quantity_str = str(quantity)
        if '.' in quantity_str:
            integer_part, decimal_part = quantity_str.split('.', 1)
            if len(decimal_part) > 6:
                decimal_part = decimal_part[:6]
            return f"{integer_part}.{decimal_part}"
        return quantity_str


def format_price(price, max_decimal_places=4):
    """
    格式化价格，确保不超过指定的小数位数（兼容旧版本）
    """
    try:
        # 转换为Decimal进行精确计算
        price_decimal = Decimal(str(price))
        
        # 根据价格大小确定合适的小数位数
        if price_decimal >= 1000:
            decimal_places = 2
        elif price_decimal >= 100:
            decimal_places = 3
        elif price_decimal >= 10:
            decimal_places = 4
        elif price_decimal >= 1:
            decimal_places = 5
        else:
            decimal_places = 6
        
        # 限制最大小数位数
        decimal_places = min(decimal_places, max_decimal_places)
        
        # 四舍五入到指定小数位数
        formatted_price = price_decimal.quantize(Decimal('0.' + '0' * decimal_places), rounding=ROUND_UP)
        
        return str(formatted_price)
    except Exception as e:
        print(f"价格格式化错误: {e}, 原始价格: {price}")
        # 如果格式化失败，使用简单的字符串截断
        price_str = str(price)
        if '.' in price_str:
            integer_part, decimal_part = price_str.split('.', 1)
            if len(decimal_part) > max_decimal_places:
                decimal_part = decimal_part[:max_decimal_places]
            return f"{integer_part}.{decimal_part}"
        return price_str


def format_quantity(quantity, max_decimal_places=6):
    """
    格式化数量，确保不超过指定的小数位数（兼容旧版本）
    """
    try:
        # 转换为Decimal进行精确计算
        quantity_decimal = Decimal(str(quantity))
        
        # 限制最大小数位数
        decimal_places = min(8, max_decimal_places)
        
        # 向下取整到指定小数位数
        formatted_quantity = quantity_decimal.quantize(Decimal('0.' + '0' * decimal_places), rounding=ROUND_DOWN)
        
        return str(formatted_quantity)
    except Exception as e:
        print(f"数量格式化错误: {e}, 原始数量: {quantity}")
        # 如果格式化失败，使用简单的字符串截断
        quantity_str = str(quantity)
        if '.' in quantity_str:
            integer_part, decimal_part = quantity_str.split('.', 1)
            if len(decimal_part) > max_decimal_places:
                decimal_part = decimal_part[:max_decimal_places]
            return f"{integer_part}.{decimal_part}"
        return quantity_str

def test_fill_history_query(account_client: Account):
    fills = account_client.get_fill_history("SOL_USDC", limit=50)
    assert len(fills) == 50

# test_fill_history_query(account)

def test_get_withdrawal(account_client: Account):
    withdrawal = account_client.get_withdrawals(limit=3)
    assert isinstance(withdrawal, list)
    assert len(withdrawal) == 3


def test_execute_order(account_client: Account):
    order = account_client.execute_order(
        symbol="ETH_USDC_PERP",
        order_type='Limit',
        side="Bid",
        quantity="0.01",
        price="4400",
        time_in_force="GTC",
    )
    assert isinstance(order, dict)
    return order

order = test_execute_order(account)

print(order)

def test_deposits(account_client: Account):
    deposits = account_client.get_deposits(limit=3)
    assert isinstance(deposits, list)
    assert len(deposits) == 3


def test_get_balances(account_client: Account):
    balances = account_client.get_balances()
    assert isinstance(balances, dict)
    assert balances

test_get_balances(account)

def test_get_deposit_address(account_client: Account):
    address = account_client.get_deposit_address("Solana")
    assert isinstance(address, dict)
    assert address

test_get_deposit_address(account)

def test_get_order_history_query(account_client: Account):
    orders = account_client.get_order_history("SOL_USDC", limit=5)
    assert isinstance(orders, list)
    assert len(orders) == 5

test_get_order_history_query(account)

def test_get_open_order(account_client: Account):
    order = account_client.get_open_orders('ETH_USDC_PERP')
    print(order)
    assert isinstance(order, dict)

print('test_get_open_orders(account)')
test_get_open_order(account)

def test_cancel_order(account_client: Account):
    status = account_client.cancel_order("ETH_USDC_PERP", order_id=order['id'])
    print(status)

test_cancel_order(account)

def test_cancel_all_orders(account_client: Account):
    cancelled_orders = account_client.cancel_all_orders("ETH_USDC_PERP")
    assert isinstance(cancelled_orders, list)


test_cancel_all_orders(account)


def hedge_strategy_with_contracts():
    """
    对冲策略：多单做BTC, ETH, SOL, DOGE, XRP, BNB, LTC均分5000，
    其他所有支持合约的币种均分500做空单
    """
    print("=" * 80)
    print("开始执行对冲策略")
    print("=" * 80)
    
    try:
        # 1. 获取所有市场信息
        print("\n1. 获取所有市场信息...")
        markets_response = public.get_markets()
        print(f"市场响应类型: {type(markets_response)}")
        
        if isinstance(markets_response, dict) and 'data' in markets_response:
            markets = markets_response['data']
        elif isinstance(markets_response, list):
            markets = markets_response
        else:
            print(f"无法解析市场数据: {markets_response}")
            return
        
        print(f"找到 {len(markets)} 个市场")
        
        # 2. 筛选出永续合约市场
        perpetual_markets = []
        for market in markets:
            if isinstance(market, dict):
                symbol = market.get('symbol', '')
                # 检查是否为永续合约（通常包含PERP或_PERP）
                if 'PERP' in symbol or '_PERP' in symbol:
                    perpetual_markets.append(market)
        
        print(f"找到 {len(perpetual_markets)} 个永续合约市场")
        
        # 3. 获取所有ticker信息
        print("\n2. 获取所有ticker信息...")
        tickers_response = public.get_tickers()
        
        if isinstance(tickers_response, dict) and 'data' in tickers_response:
            tickers = tickers_response['data']
        elif isinstance(tickers_response, list):
            tickers = tickers_response
        else:
            print(f"无法解析ticker数据: {tickers_response}")
            return
        
        # 创建ticker字典，方便查找价格
        ticker_dict = {}
        for ticker in tickers:
            if isinstance(ticker, dict):
                symbol = ticker.get('symbol', '')
                last_price = ticker.get('lastPrice', '0')
                ticker_dict[symbol] = last_price
        
        print(f"获取到 {len(ticker_dict)} 个ticker价格信息")
        
        # 4. 定义多单币种和金额分配
        long_coins = ['BTC', 'ETH', 'SOL', 'DOGE', 'XRP', 'BNB', 'LTC']
        long_total_amount = 5000  # 多单总金额
        long_amount_per_coin = long_total_amount / len(long_coins)
        
        # 5. 定义空单金额分配
        short_total_amount = 5000  # 空单总金额
        short_coins = []
        
        # 找出所有非多单币种的永续合约
        for market in perpetual_markets:
            symbol = market.get('symbol', '')
            # 提取基础币种（去掉_USDC_PERP等后缀）
            base_coin = symbol.split('_')[0] if '_' in symbol else symbol
            if base_coin not in long_coins and base_coin not in short_coins:
                short_coins.append(base_coin)
        
        short_amount_per_coin = short_total_amount / len(short_coins) if short_coins else 0
        
        print(f"\n多单币种: {long_coins}, 每个币种金额: ${long_amount_per_coin:.2f}")
        print(f"空单币种数量: {len(short_coins)}, 每个币种金额: ${short_amount_per_coin:.2f}")
        
        # 6. 执行多单
        print("\n3. 执行多单...")
        long_orders = []
        
        for coin in long_coins:
            # 查找对应的永续合约symbol
            symbol = None
            for market in perpetual_markets:
                if market.get('symbol', '').startswith(f"{coin}_"):
                    symbol = market.get('symbol', '')
                    break
            
            if not symbol:
                print(f"  未找到 {coin} 的永续合约")
                continue
                
            if symbol not in ticker_dict:
                print(f"  未找到 {symbol} 的价格信息")
                continue
            
            try:
                current_price = float(ticker_dict[symbol])
                # 多单价格低于当前价格千分之三
                order_price = current_price * 0.997
                # 计算下单量
                quantity = long_amount_per_coin / order_price
                
                # 使用动态精度格式化价格和数量
                formatted_price = format_price_with_precision(order_price, symbol, current_price)
                formatted_quantity = format_quantity_with_precision(quantity, symbol, current_price)
                
                print(f"  {coin} ({symbol}): 当前价格=${current_price:.4f}, 下单价格=${formatted_price}, 数量={formatted_quantity}")
                
                order = account.execute_order(
                    symbol=symbol,
                    side="Bid",  # 买入
                    order_type="Limit",
                    quantity=formatted_quantity,
                    price=formatted_price,
                    time_in_force="GTC",  # 持久有效
                    post_only=True  # 只做挂单
                )
                
                if order:
                    long_orders.append(order)
                    print(f"  ✓ {coin} 多单下单成功: {order.get('id', order)}")
                else:
                    print(f"  ✗ {coin} 多单下单失败")
                    
            except Exception as e:
                print(f"  ✗ {coin} 多单下单异常: {e}")
        
        # 7. 执行空单
        print("\n4. 执行空单...")
        short_orders = []
        
        for coin in short_coins:
            # 查找对应的永续合约symbol
            symbol = None
            for market in perpetual_markets:
                if market.get('symbol', '').startswith(f"{coin}_"):
                    symbol = market.get('symbol', '')
                    break
            
            if not symbol:
                print(f"  未找到 {coin} 的永续合约")
                continue
                
            if symbol not in ticker_dict:
                print(f"  未找到 {symbol} 的价格信息")
                continue
            
            try:
                current_price = float(ticker_dict[symbol])
                # 空单价格高于当前价格千分之三
                order_price = current_price * 1.003
                # 计算下单量
                quantity = short_amount_per_coin / order_price
                
                # 使用动态精度格式化价格和数量
                formatted_price = format_price_with_precision(order_price, symbol, current_price)
                formatted_quantity = format_quantity_with_precision(quantity, symbol, current_price)
                
                print(f"  {coin} ({symbol}): 当前价格=${current_price:.4f}, 下单价格=${formatted_price}, 数量={formatted_quantity}")
                
                order = account.execute_order(
                    symbol=symbol,
                    side="Ask",  # 卖出
                    order_type="Limit",
                    quantity=formatted_quantity,
                    price=formatted_price,
                    time_in_force="GTC",  # 持久有效
                    post_only=True  # 只做挂单
                )
                
                if order:
                    short_orders.append(order)
                    print(f"  ✓ {coin} 空单下单成功: {order.get('id', order)}")
                else:
                    print(f"  ✗ {coin} 空单下单失败")
                    
            except Exception as e:
                print(f"  ✗ {coin} 空单下单异常: {e}")
        
        # 8. 总结
        print("\n" + "=" * 80)
        print("对冲策略执行完成")
        print("=" * 80)
        print(f"多单成功下单: {len(long_orders)} 个")
        print(f"空单成功下单: {len(short_orders)} 个")
        print(f"总订单数: {len(long_orders) + len(short_orders)} 个")
        
        if long_orders:
            print("\n多单订单详情:")
            for i, order in enumerate(long_orders, 1):
                print(f"  {i}. 订单ID: {order.get('id', 'N/A')}, 状态: {order.get('status', 'N/A')}")
        
        if short_orders:
            print("\n空单订单详情:")
            for i, order in enumerate(short_orders, 1):
                print(f"  {i}. 订单ID: {order.get('id', 'N/A')}, 状态: {order.get('status', 'N/A')}")
        
        return {
            'long_orders': long_orders,
            'short_orders': short_orders,
            'long_coins': long_coins,
            'short_coins': short_coins
        }
        
    except Exception as e:
        print(f"\n对冲策略执行失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_hedge_strategy():
    """测试对冲策略"""
    print("开始测试对冲策略...")
    result = hedge_strategy_with_contracts()
    if result:
        print("对冲策略测试完成")
    else:
        print("对冲策略测试失败")


def test_hedge_strategy_dry_run():
    """
    对冲策略干跑测试 - 只获取市场信息和价格，不实际下单
    """
    print("=" * 80)
    print("对冲策略干跑测试（不实际下单）")
    print("=" * 80)
    
    try:
        # 1. 获取所有市场信息
        print("\n1. 获取所有市场信息...")
        markets_response = public.get_markets()
        print(f"市场响应类型: {type(markets_response)}")
        
        if isinstance(markets_response, dict) and 'data' in markets_response:
            markets = markets_response['data']
        elif isinstance(markets_response, list):
            markets = markets_response
        else:
            print(f"无法解析市场数据: {markets_response}")
            return
        
        print(f"找到 {len(markets)} 个市场")
        
        # 2. 筛选出永续合约市场
        perpetual_markets = []
        for market in markets:
            if isinstance(market, dict):
                symbol = market.get('symbol', '')
                # 检查是否为永续合约（通常包含PERP或_PERP）
                if 'PERP' in symbol or '_PERP' in symbol:
                    perpetual_markets.append(market)
        
        print(f"找到 {len(perpetual_markets)} 个永续合约市场")
        
        # 3. 获取所有ticker信息
        print("\n2. 获取所有ticker信息...")
        tickers_response = public.get_tickers()
        
        if isinstance(tickers_response, dict) and 'data' in tickers_response:
            tickers = tickers_response['data']
        elif isinstance(tickers_response, list):
            tickers = tickers_response
        else:
            print(f"无法解析ticker数据: {tickers_response}")
            return
        
        # 创建ticker字典，方便查找价格
        ticker_dict = {}
        for ticker in tickers:
            if isinstance(ticker, dict):
                symbol = ticker.get('symbol', '')
                last_price = ticker.get('lastPrice', '0')
                ticker_dict[symbol] = last_price
        
        print(f"获取到 {len(ticker_dict)} 个ticker价格信息")
        
        # 4. 定义多单币种和金额分配
        long_coins = ['BTC', 'ETH', 'SOL', 'DOGE', 'XRP', 'BNB', 'LTC']
        long_total_amount = 5000  # 多单总金额
        long_amount_per_coin = long_total_amount / len(long_coins)
        
        # 5. 定义空单金额分配
        short_total_amount = 500  # 空单总金额
        short_coins = []
        
        # 找出所有非多单币种的永续合约
        for market in perpetual_markets:
            symbol = market.get('symbol', '')
            # 提取基础币种（去掉_USDC_PERP等后缀）
            base_coin = symbol.split('_')[0] if '_' in symbol else symbol
            if base_coin not in long_coins and base_coin not in short_coins:
                short_coins.append(base_coin)
        
        short_amount_per_coin = short_total_amount / len(short_coins) if short_coins else 0
        
        print(f"\n多单币种: {long_coins}, 每个币种金额: ${long_amount_per_coin:.2f}")
        print(f"空单币种数量: {len(short_coins)}, 每个币种金额: ${short_amount_per_coin:.2f}")
        
        # 6. 模拟多单下单
        print("\n3. 模拟多单下单...")
        long_orders = []
        
        for coin in long_coins:
            # 查找对应的永续合约symbol
            symbol = None
            for market in perpetual_markets:
                if market.get('symbol', '').startswith(f"{coin}_"):
                    symbol = market.get('symbol', '')
                    break
            
            if not symbol:
                print(f"  未找到 {coin} 的永续合约")
                continue
                
            if symbol not in ticker_dict:
                print(f"  未找到 {symbol} 的价格信息")
                continue
            
            try:
                current_price = float(ticker_dict[symbol])
                # 多单价格低于当前价格千分之三
                order_price = current_price * 0.997
                # 计算下单量
                quantity = long_amount_per_coin / order_price
                
                # 格式化价格和数量
                formatted_price = format_price(order_price)
                formatted_quantity = format_quantity(quantity)
                
                print(f"  {coin} ({symbol}): 当前价格=${current_price:.4f}, 下单价格=${formatted_price}, 数量={formatted_quantity}")
                
                # 模拟订单
                mock_order = {
                    'symbol': symbol,
                    'side': 'Bid',
                    'price': float(formatted_price),
                    'quantity': float(formatted_quantity),
                    'coin': coin,
                    'amount': long_amount_per_coin
                }
                long_orders.append(mock_order)
                print(f"  ✓ {coin} 多单模拟成功")
                    
            except Exception as e:
                print(f"  ✗ {coin} 多单模拟异常: {e}")
        
        # 7. 模拟空单下单
        print("\n4. 模拟空单下单...")
        short_orders = []
        
        for coin in short_coins:
            # 查找对应的永续合约symbol
            symbol = None
            for market in perpetual_markets:
                if market.get('symbol', '').startswith(f"{coin}_"):
                    symbol = market.get('symbol', '')
                    break
            
            if not symbol:
                print(f"  未找到 {coin} 的永续合约")
                continue
                
            if symbol not in ticker_dict:
                print(f"  未找到 {symbol} 的价格信息")
                continue
            
            try:
                current_price = float(ticker_dict[symbol])
                # 空单价格高于当前价格千分之三
                order_price = current_price * 1.003
                # 计算下单量
                quantity = short_amount_per_coin / order_price
                
                # 格式化价格和数量
                formatted_price = format_price(order_price)
                formatted_quantity = format_quantity(quantity)
                
                print(f"  {coin} ({symbol}): 当前价格=${current_price:.4f}, 下单价格=${formatted_price}, 数量={formatted_quantity}")
                
                # 模拟订单
                mock_order = {
                    'symbol': symbol,
                    'side': 'Ask',
                    'price': float(formatted_price),
                    'quantity': float(formatted_quantity),
                    'coin': coin,
                    'amount': short_amount_per_coin
                }
                short_orders.append(mock_order)
                print(f"  ✓ {coin} 空单模拟成功")
                    
            except Exception as e:
                print(f"  ✗ {coin} 空单模拟异常: {e}")
        
        # 8. 总结
        print("\n" + "=" * 80)
        print("对冲策略干跑测试完成")
        print("=" * 80)
        print(f"多单模拟订单: {len(long_orders)} 个")
        print(f"空单模拟订单: {len(short_orders)} 个")
        print(f"总模拟订单数: {len(long_orders) + len(short_orders)} 个")
        
        # 计算总金额
        total_long_amount = sum(order['amount'] for order in long_orders)
        total_short_amount = sum(order['amount'] for order in short_orders)
        print(f"多单总金额: ${total_long_amount:.2f}")
        print(f"空单总金额: ${total_short_amount:.2f}")
        print(f"总投入金额: ${total_long_amount + total_short_amount:.2f}")
        
        if long_orders:
            print("\n多单订单详情:")
            for i, order in enumerate(long_orders, 1):
                print(f"  {i}. {order['coin']} ({order['symbol']}): ${order['amount']:.2f} @ ${order['price']:.4f}")
        
        if short_orders:
            print("\n空单订单详情:")
            for i, order in enumerate(short_orders, 1):
                print(f"  {i}. {order['coin']} ({order['symbol']}): ${order['amount']:.2f} @ ${order['price']:.4f}")
        
        return {
            'long_orders': long_orders,
            'short_orders': short_orders,
            'long_coins': long_coins,
            'short_coins': short_coins
        }
        
    except Exception as e:
        print(f"\n对冲策略干跑测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None


# 运行对冲策略（取消注释以执行）
# test_hedge_strategy()

# 运行干跑测试（推荐先运行这个）
# test_hedge_strategy_dry_run()