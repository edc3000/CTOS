#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETH <-> WETH 转换测试脚本
"""

from driver import BaseDriver
import os

def test_eth_weth_conversion():
    """测试ETH到WETH的转换功能"""
    
    # 检查私钥
    pk = os.getenv("BASE_PRIVATE_KEY")
    if not pk:
        print("⚠️  请设置环境变量 BASE_PRIVATE_KEY")
        print("示例: export BASE_PRIVATE_KEY='your_private_key_here'")
        return
    
    try:
        # 初始化driver
        base = BaseDriver(pk)
        print("🔗 已连接到Base网络")
        print(f"📍 钱包地址: {base.address}")
        
        # 获取余额
        eth_balance = base.get_eth_balance()
        weth_balance = base.fetch_balance().get(base.WETH, 0)
        
        print(f"💰ETH余额: {eth_balance:.6f} ETH")
        print(f"💰WETH余额: {weth_balance:.6f} WETH")
        
        # 获取gas价格
        try:
            gas_price = base.w3.eth.gas_price
            gas_price_gwei = base.w3.from_wei(gas_price, 'gwei')
            print(f"⛽ 当前Gas价格: {gas_price_gwei:.2f} Gwei")
        except Exception as e:
            print(f"⚠️  获取Gas价格失败: {e}")
        
        # 测试ETH到WETH转换
        if eth_balance > 0.01:
            print("\n🔄 测试ETH->WETH转换...")
            convert_amount = min(0.005, eth_balance - 0.005)  # 保留0.005 ETH作为gas
            print(f"   转换数量: {convert_amount:.6f} ETH")
            
            tx_hash = base.eth_to_weth(convert_amount)
            if tx_hash:
                print(f"✅ ETH->WETH转换成功: {tx_hash}")
                
                # 检查转换后的余额
                new_weth_balance = base.fetch_balance().get(base.WETH, 0)
                print(f"   转换后WETH余额: {new_weth_balance:.6f} WETH")
                
                # 测试WETH到ETH转换
                if new_weth_balance > 0.001:
                    print("\n🔄 测试WETH->ETH转换...")
                    withdraw_amount = min(0.001, new_weth_balance)
                    print(f"   转换数量: {withdraw_amount:.6f} WETH")
                    
                    tx_hash = base.weth_to_eth(withdraw_amount)
                    if tx_hash:
                        print(f"✅ WETH->ETH转换成功: {tx_hash}")
                        
                        # 检查最终余额
                        final_eth_balance = base.get_eth_balance()
                        final_weth_balance = base.fetch_balance().get(base.WETH, 0)
                        print(f"   最终ETH余额: {final_eth_balance:.6f} ETH")
                        print(f"   最终WETH余额: {final_weth_balance:.6f} WETH")
                    else:
                        print("❌ WETH->ETH转换失败")
            else:
                print("❌ ETH->WETH转换失败")
        else:
            print("⚠️  ETH余额不足，需要至少0.01 ETH来测试转换功能")
            print("💡 提示：您可以向钱包地址发送一些ETH来测试")
            print(f"   钱包地址: {base.address}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    test_eth_weth_conversion()
