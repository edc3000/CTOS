# -*- coding: utf-8 -*-
# ctos/drivers/aster/test_aster_driver.py
# Aster DEX driver 测试文件

from __future__ import print_function
import sys
import os

# 添加项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../../..'))
sys.path.insert(0, project_root)

from ctos.drivers.aster.driver import AsterDriver

def test_aster_driver():
    """测试Aster driver的基本功能"""
    print("=" * 50)
    print("开始测试 Aster Driver")
    print("=" * 50)
    
    try:
        # 初始化driver
        driver = AsterDriver(account_id=0)
        print(f"Aster Driver 初始化成功: {driver}")
        print()
        
        # 测试获取价格
        print("[ASTER_TEST] before call: get_price_now")
        price = driver.get_price_now('ETH-USDT')
        print(f"[ASTER_TEST] after call: get_price_now -> {price}")
        print()
        
        # 测试获取订单簿
        print("[ASTER_TEST] before call: get_orderbook")
        orderbook = driver.get_orderbook('ETH-USDT')
        print(f"[ASTER_TEST] after call: get_orderbook -> {orderbook['symbol']}")
        print()
        
        # 测试获取K线
        print("[ASTER_TEST] before call: get_klines")
        klines, err = driver.get_klines('ETH-USDT', '1h', 20)
        print(f"[ASTER_TEST] after call: get_klines -> {type(klines)}")
        if err:
            print(f"Error: {err}")
        print()
        
        # 测试下单
        print("[ASTER_TEST] before call: place_order")
        order_id, err = driver.place_order('ETH-USDT', 'buy', 'limit', 0.01, 3500.0)
        print(f"[ASTER_TEST] after call: place_order -> ('{order_id}', {err})")
        print()
        
        # 测试修改订单
        print("[ASTER_TEST] before call: amend_order")
        order_id, err = driver.amend_order(order_id, 'ETH-USDT', price=3600.0)
        print(f"[ASTER_TEST] after call: amend_order -> ('{order_id}', {err})")
        print()
        
        # 测试获取订单状态
        print("[ASTER_TEST] before call: get_order_status")
        order_status, err = driver.get_order_status(order_id)
        print(f"[ASTER_TEST] after call: get_order_status -> {order_status}")
        print()
        
        # 测试获取未成交订单
        print("[ASTER_TEST] before call: get_open_orders only Orderids")
        open_orders, err = driver.get_open_orders('ETH-USDT', onlyOrderId=True)
        print(f"[ASTER_TEST] after call: get_open_orders -> {open_orders}")
        print()
        
        print("[ASTER_TEST] before call: get_open_orders all infos")
        open_orders, err = driver.get_open_orders('ETH-USDT', onlyOrderId=False)
        print(f"[ASTER_TEST] after call: get_open_orders -> {open_orders}")
        print()
        
        # 测试撤销订单
        print("[ASTER_TEST] before call: revoke_order")
        success, err = driver.revoke_order(order_id)
        print(f"[ASTER_TEST] after call: revoke_order -> ({success}, {err})")
        print()
        
        # 测试撤销所有订单
        print("[ASTER_TEST] before call: cancel_all (no symbol)")
        try:
            result = driver.cancel_all()
            print(f"[ASTER_TEST] after call: cancel_all (no symbol) -> {result}")
        except Exception as e:
            print(f"[ASTER_TEST] after call: cancel_all (no symbol) raised: {e}")
        print()
        
        print("[ASTER_TEST] before call: cancel_all (with symbol)")
        try:
            result = driver.cancel_all('ETH-USDT')
            print(f"[ASTER_TEST] after call: cancel_all (with symbol) -> {result}")
        except Exception as e:
            print(f"[ASTER_TEST] after call: cancel_all (with symbol) raised: {e}")
        print()
        
        # 测试获取余额
        print("[ASTER_TEST] before call: fetch_balance")
        balance = driver.fetch_balance('USDT')
        print(f"[ASTER_TEST] after call: fetch_balance -> {balance}")
        print()
        
        # 测试获取持仓
        print("[ASTER_TEST] before call: get_position")
        position, err = driver.get_position('ETH-USDT')
        print(f"[ASTER_TEST] after call: get_position -> {position}")
        print()
        
        # 测试获取交易对列表
        print("[ASTER_TEST] before call: symbols")
        symbols, err = driver.symbols('SPOT')
        print(f"[ASTER_TEST] after call: symbols -> {symbols[:10]}")  # 只显示前10个
        print()
        
        # 测试获取交易所限制
        print("[ASTER_TEST] before call: exchange_limits")
        limits, err = driver.exchange_limits('ETH-USDT')
        print(f"[ASTER_TEST] after call: exchange_limits -> {limits}")
        print()
        
        # 测试获取费率
        print("[ASTER_TEST] before call: fees")
        fees, err = driver.fees('ETH-USDT')
        print(f"[ASTER_TEST] after call: fees -> {fees}")
        print()
        
        print("=" * 50)
        print("Aster Driver 测试完成")
        print("=" * 50)
        
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_aster_driver()
