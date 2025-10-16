#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试类型转换修复
"""

from web3 import Web3
from eth_account import Account
import os

def test_type_conversion():
    """测试类型转换修复"""
    
    # 检查私钥
    pk = os.getenv("BASE_PRIVATE_KEY")
    if not pk:
        print("⚠️  请设置环境变量 BASE_PRIVATE_KEY")
        return
    
    try:
        # 初始化web3
        w3 = Web3(Web3.HTTPProvider("https://mainnet.base.org"))
        assert w3.is_connected(), "无法连接 Base 网络"
        
        # 创建账户
        account = Account.from_key(pk)
        address = account.address
        
        print("🔗 已连接到Base网络")
        print(f"📍 钱包地址: {address}")
        
        # 测试ETH余额获取
        balance = w3.eth.get_balance(address)
        eth_balance = float(w3.from_wei(balance, 'ether'))
        print(f"💰ETH余额: {eth_balance:.6f} ETH")
        
        # 测试代币余额获取
        USDC = Web3.to_checksum_address("0x833589fcd6edb6e08f4c7c32d4f71b54bda02913")
        WETH = Web3.to_checksum_address("0x4200000000000000000000000000000000000006")
        
        ABI_ERC20 = [
            {
                "name": "balanceOf",
                "inputs": [{"name": "owner", "type": "address"}],
                "outputs": [{"name": "balance", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]
        
        # 获取USDC余额
        usdc_contract = w3.eth.contract(address=USDC, abi=ABI_ERC20)
        usdc_balance_raw = usdc_contract.functions.balanceOf(address).call()
        usdc_balance = float(usdc_balance_raw) / (10 ** 6)  # USDC 6位小数
        print(f"💰USDC余额: {usdc_balance:.6f} USDC")
        
        # 获取WETH余额
        weth_contract = w3.eth.contract(address=WETH, abi=ABI_ERC20)
        weth_balance_raw = weth_contract.functions.balanceOf(address).call()
        weth_balance = float(weth_balance_raw) / (10 ** 18)  # WETH 18位小数
        print(f"💰WETH余额: {weth_balance:.6f} WETH")
        
        # 测试类型转换
        print("\n🔄 测试类型转换...")
        test_amount = 0.001
        converted_amount = float(weth_balance) - test_amount
        print(f"   转换测试: {weth_balance:.6f} - {test_amount:.6f} = {converted_amount:.6f}")
        
        # 获取gas价格
        gas_price = w3.eth.gas_price
        gas_price_gwei = float(w3.from_wei(gas_price, 'gwei'))
        print(f"⛽ 当前Gas价格: {gas_price_gwei:.2f} Gwei")
        
        print("✅ 类型转换测试通过！")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_type_conversion()
