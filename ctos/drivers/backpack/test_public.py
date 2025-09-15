from bpx.base.base_public import BasePublic
from bpx.public import Public
from bpx.exceptions import NegativeValueError, InvalidTimeIntervalError, LimitValueError
import json


def create_base_public():
    return BasePublic()


def create_public_client():
    return Public()


def test_get_assets_url(base_public):
    """测试获取资产列表URL"""
    # 测试用例1: 验证返回正确的资产URL
    assert base_public.get_assets_url() == "https://api.backpack.exchange/api/v1/assets"


def test_get_markets_url(base_public):
    assert (
        base_public.get_markets_url() == "https://api.backpack.exchange/api/v1/markets"
    )


def test_get_ticker_url(base_public):
    symbol = "BTC_USD"
    expected_url = "https://api.backpack.exchange/api/v1/ticker?symbol=BTC_USD"
    assert base_public.get_ticker_url(symbol) == expected_url


def test_get_depth_url(base_public):
    symbol = "BTC_USD"
    expected_url = "https://api.backpack.exchange/api/v1/depth?symbol=BTC_USD"
    assert base_public.get_depth_url(symbol) == expected_url


def test_get_klines_url(base_public):
    symbol = "BTC_USD"
    interval = "1m"
    start_time = 1609459200
    end_time = 1609462800
    expected_url = "https://api.backpack.exchange/api/v1/klines?symbol=BTC_USD&interval=1m&startTime=1609459200&endTime=1609462800"
    assert (
        base_public.get_klines_url(symbol, interval, start_time, end_time)
        == expected_url
    )

    with pytest.raises(NegativeValueError):
        base_public.get_klines_url(symbol, interval, -1, end_time)

    with pytest.raises(InvalidTimeIntervalError):
        base_public.get_klines_url(symbol, "10x", start_time, end_time)


def test_get_recent_trades_url(base_public):
    symbol = "BTC_USD"
    limit = 100
    expected_url = (
        "https://api.backpack.exchange/api/v1/trades?symbol=BTC_USD&limit=100"
    )
    assert base_public.get_recent_trades_url(symbol, limit) == expected_url

    with pytest.raises(LimitValueError):
        base_public.get_recent_trades_url(symbol, -1)

    with pytest.raises(LimitValueError):
        base_public.get_recent_trades_url(symbol, 1001)


def test_get_status_url(base_public):
    assert base_public.get_status_url() == "https://api.backpack.exchange/api/v1/status"


def test_get_ping_url(base_public):
    assert base_public.get_ping_url() == "https://api.backpack.exchange/api/v1/ping"


def test_get_time_url(base_public):
    assert base_public.get_time_url() == "https://api.backpack.exchange/api/v1/time"


# ==================== 实际API调用测试 ====================

def test_actual_api_calls():
    """测试实际的API调用功能"""
    print("\n" + "=" * 80)
    print("Backpack Public API 实际调用测试")
    print("=" * 80)
    
    client = Public()
    
    # 1. 测试获取资产列表
    print("\n1. 测试 get_assets() - 获取资产列表:")
    try:
        result = client.get_assets()
        print(f"   状态: 成功")
        print(f"   数据类型: {type(result)}")
        if isinstance(result, dict):
            print(f"   响应键: {list(result.keys())}")
        elif isinstance(result, list):
            print(f"   资产数量: {len(result)}")
            if result:
                print(f"   第一个资产示例: {result[0]}")
        print(f"   原始响应: {json.dumps(result, indent=2, ensure_ascii=False)[:500]}...")
    except Exception as e:
        print(f"   状态: 失败 - {e}")
    
    # 2. 测试获取市场列表
    print("\n2. 测试 get_markets() - 获取市场列表:")
    try:
        result = client.get_markets()
        print(f"   状态: 成功")
        print(f"   数据类型: {type(result)}")
        if isinstance(result, dict):
            print(f"   响应键: {list(result.keys())}")
        elif isinstance(result, list):
            print(f"   市场数量: {len(result)}")
            if result:
                print(f"   第一个市场示例: {result[0]}")
        print(f"   原始响应: {json.dumps(result, indent=2, ensure_ascii=False)[:500]}...")
    except Exception as e:
        print(f"   状态: 失败 - {e}")
    
    # 3. 测试获取状态
    print("\n3. 测试 get_status() - 获取系统状态:")
    try:
        result = client.get_status()
        print(f"   状态: 成功")
        print(f"   数据类型: {type(result)}")
        print(f"   原始响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
    except Exception as e:
        print(f"   状态: 失败 - {e}")
    
    # 4. 测试ping
    print("\n4. 测试 get_ping() - 测试连接:")
    try:
        result = client.get_ping()
        print(f"   状态: 成功")
        print(f"   数据类型: {type(result)}")
        print(f"   原始响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
    except Exception as e:
        print(f"   状态: 失败 - {e}")
    
    # 5. 测试获取服务器时间
    print("\n5. 测试 get_time() - 获取服务器时间:")
    try:
        result = client.get_time()
        print(f"   状态: 成功")
        print(f"   数据类型: {type(result)}")
        print(f"   原始响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
    except Exception as e:
        print(f"   状态: 失败 - {e}")
    
    # 6. 测试获取ticker信息（需要有效的交易对）
    print("\n6. 测试 get_ticker() - 获取ticker信息:")
    try:
        # 先获取市场列表来找到有效的交易对
        markets = client.get_markets()
        if isinstance(markets, list) and markets:
            symbol = markets[0].get('symbol', 'BTC_USD')  # 使用第一个市场的symbol
        else:
            symbol = 'BTC_USD'  # 默认值
        
        result = client.get_ticker(symbol)
        print(f"   状态: 成功")
        print(f"   交易对: {symbol}")
        print(f"   数据类型: {type(result)}")
        print(f"   原始响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
    except Exception as e:
        print(f"   状态: 失败 - {e}")
    
    # 7. 测试获取深度信息
    print("\n7. 测试 get_depth() - 获取深度信息:")
    try:
        # 使用相同的symbol
        if 'symbol' in locals():
            result = client.get_depth(symbol)
            print(f"   状态: 成功")
            print(f"   交易对: {symbol}")
            print(f"   数据类型: {type(result)}")
            print(f"   原始响应: {json.dumps(result, indent=2, ensure_ascii=False)[:500]}...")
        else:
            print(f"   状态: 跳过 - 没有有效的交易对")
    except Exception as e:
        print(f"   状态: 失败 - {e}")
    
    # 8. 测试获取最近交易
    print("\n8. 测试 get_recent_trades() - 获取最近交易:")
    try:
        if 'symbol' in locals():
            result = client.get_recent_trades(symbol, 10)  # 只获取10条记录
            print(f"   状态: 成功")
            print(f"   交易对: {symbol}")
            print(f"   数据类型: {type(result)}")
            if isinstance(result, list):
                print(f"   交易记录数: {len(result)}")
            print(f"   原始响应: {json.dumps(result, indent=2, ensure_ascii=False)[:500]}...")
        else:
            print(f"   状态: 跳过 - 没有有效的交易对")
    except Exception as e:
        print(f"   状态: 失败 - {e}")
    
    print("\n" + "=" * 80)
    print("API调用测试完成！")
    print("=" * 80)


def run_url_examples():
    """运行URL生成函数的示例"""
    print("\n" + "=" * 60)
    print("Backpack Public API URL生成函数示例")
    print("=" * 60)
    
    base_public = BasePublic()
    
    # 测试 get_assets_url
    print("\n1. get_assets_url() 函数:")
    print(f"   结果: {base_public.get_assets_url()}")
    
    # 测试 get_markets_url
    print("\n2. get_markets_url() 函数:")
    print(f"   结果: {base_public.get_markets_url()}")
    
    # 测试 get_ticker_url
    print("\n3. get_ticker_url(symbol) 函数:")
    symbol = "BTC_USD"
    print(f"   输入: symbol='{symbol}'")
    print(f"   结果: {base_public.get_ticker_url(symbol)}")
    
    # 测试 get_depth_url
    print("\n4. get_depth_url(symbol) 函数:")
    symbol = "BTC_USD"
    print(f"   输入: symbol='{symbol}'")
    print(f"   结果: {base_public.get_depth_url(symbol)}")
    
    # 测试 get_klines_url
    print("\n5. get_klines_url(symbol, interval, start_time, end_time) 函数:")
    symbol = "BTC_USD"
    interval = "1m"
    start_time = 1609459200
    end_time = 1609462800
    print(f"   输入: symbol='{symbol}', interval='{interval}', start_time={start_time}, end_time={end_time}")
    print(f"   结果: {base_public.get_klines_url(symbol, interval, start_time, end_time)}")
    
    # 测试异常情况
    print("\n   异常测试:")
    try:
        base_public.get_klines_url(symbol, interval, -1, end_time)
    except NegativeValueError as e:
        print(f"   NegativeValueError: {e}")
    
    try:
        base_public.get_klines_url(symbol, "10x", start_time, end_time)
    except InvalidTimeIntervalError as e:
        print(f"   InvalidTimeIntervalError: {e}")
    
    # 测试 get_recent_trades_url
    print("\n6. get_recent_trades_url(symbol, limit) 函数:")
    symbol = "BTC_USD"
    limit = 100
    print(f"   输入: symbol='{symbol}', limit={limit}")
    print(f"   结果: {base_public.get_recent_trades_url(symbol, limit)}")
    
    # 测试异常情况
    print("\n   异常测试:")
    try:
        base_public.get_recent_trades_url(symbol, -1)
    except LimitValueError as e:
        print(f"   LimitValueError (limit=-1): {e}")
    
    try:
        base_public.get_recent_trades_url(symbol, 1001)
    except LimitValueError as e:
        print(f"   LimitValueError (limit=1001): {e}")
    
    # 测试 get_status_url
    print("\n7. get_status_url() 函数:")
    print(f"   结果: {base_public.get_status_url()}")
    
    # 测试 get_ping_url
    print("\n8. get_ping_url() 函数:")
    print(f"   结果: {base_public.get_ping_url()}")
    
    # 测试 get_time_url
    print("\n9. get_time_url() 函数:")
    print(f"   结果: {base_public.get_time_url()}")
    
    print("\n" + "=" * 60)
    print("URL生成函数示例完成！")
    print("=" * 60)


if __name__ == "__main__":
    print("选择运行模式:")
    print("1. 运行URL生成函数示例")
    print("2. 运行实际API调用测试")
    print("3. 运行所有测试")
    
    choice = input("\n请输入选择 (1/2/3): ").strip()
    
    if choice == "1":
        run_url_examples()
    elif choice == "2":
        test_actual_api_calls()
    elif choice == "3":
        run_url_examples()
        test_actual_api_calls()
    else:
        print("无效选择，运行默认测试...")
        run_url_examples()
        test_actual_api_calls()