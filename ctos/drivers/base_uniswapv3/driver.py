# -*- coding: utf-8 -*-
# ctos/drivers/base_uniswapv3/driver.py
# Base-chain Uniswap V3 driver (CTOS-style, with liquidity tracking)
#
# 使用示例:
#   base = BaseDriver(private_key="your_key")
#   
#   # 支持多种币种格式
#   price = base.get_price_now("USDC-WETH")  # 标准格式
#   price = base.get_price_now("usdc")       # 单个币种，自动推断交易对
#   price = base.get_price_now("weth-usdc")  # 反向格式
#   
#   # 余额查询
#   balance = base.fetch_balance("USDC")     # 通过币种名称
#   balance = base.fetch_balance("0x...")    # 通过合约地址
#   
#   # 交易
#   tx_hash, error = base.buy("usdc", 100)   # 买入100 USDC的WETH
#   tx_hash, error = base.sell("weth", 0.1)  # 卖出0.1 WETH
#   
#   # 添加流动性
#   tx_hash = base.add_liquidity(100, 0.05, symbol="USDC-WETH")

from web3 import Web3
from eth_account import Account
import time
import os
import json
from typing import Optional, Dict, Any


class BaseDriver:
    """
    Uniswap V3 driver on Base chain.
    支持 swap、add/remove liquidity、collect fees、get_position。
    """
    def __init__(self, private_key=None, rpc_url="https://mainnet.base.org"):
        self.cex = 'Base'
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        assert self.w3.is_connected(), "无法连接 Base 网络"

        # Base链上的Uniswap V3合约地址（使用校验和地址）
        self.ROUTER = Web3.to_checksum_address("0x2626664c2603336E57B271c5C0b26F421741e481")  # SwapRouter
        self.QUOTER_V2 = Web3.to_checksum_address("0x3d4e44Eb1374240CE5F1B871ab261CD16335B76a")  # QuoterV2
        self.POSITION_MANAGER = Web3.to_checksum_address("0x2F3A40A3db8a7e3D09B0adfC1Bae66A9B0a6F7cD")  # NonfungiblePositionManager

        # 常用代币（使用校验和地址）
        self.USDC = Web3.to_checksum_address("0x833589fcd6edb6e08f4c7c32d4f71b54bda02913")
        self.WETH = Web3.to_checksum_address("0x4200000000000000000000000000000000000006")
        self.FEE = 500  # 0.05%

        # 钱包
        if private_key:
            try:
                self.account = Account.from_key(private_key)
                self.address = self.account.address
            except Exception as e:
                print(f"❌ 私钥错误: {e}")
                self.account = None
                self.address = None
        else:
            self.account = None
            self.address = None

        # 状态记录
        self.positions = {}  # tokenId -> {symbol, liquidity, tokens}

        self._load_abi()

    def _norm_symbol(self, symbol):
        """
        格式化币种名称，支持多种输入格式
        支持格式: 'USDC-WETH', 'USDC/WETH', 'usdc-weth', 'usdc', 'WETH'
        返回: (formatted_symbol, base_token, quote_token, base_address, quote_address)
        """
        if not symbol:
            return None, None, None, None, None
            
        s = str(symbol).replace("/", "-").upper()
        
        # 处理不同的输入格式
        if "-" in s:
            parts = s.split("-")
            base = parts[0]
            quote = parts[1] if len(parts) > 1 else None
        else:
            # 单个币种，需要推断交易对
            if s in ['USDC', 'WETH']:
                base = s
                quote = 'WETH' if s == 'USDC' else 'USDC'
            else:
                # 默认作为base，quote为USDC
                base = s
                quote = 'USDC'
        
        # 构建标准格式
        formatted_symbol = f"{base}-{quote}"
        
        # 映射到合约地址
        token_addresses = {
            'USDC': self.USDC,
            'WETH': self.WETH,
            'ETH': self.WETH  # ETH映射到WETH
        }
        
        base_address = token_addresses.get(base)
        quote_address = token_addresses.get(quote)
        
        return formatted_symbol, base, quote, base_address, quote_address

    def _load_abi(self):
        """载入 ABI"""
        # Position Manager ABI
        self.ABI_POSITION_MANAGER = [
            {
                "name": "positions",
                "inputs": [{"name": "tokenId", "type": "uint256"}],
                "outputs": [
                    {"name": "nonce", "type": "uint96"},
                    {"name": "operator", "type": "address"},
                    {"name": "token0", "type": "address"},
                    {"name": "token1", "type": "address"},
                    {"name": "fee", "type": "uint24"},
                    {"name": "tickLower", "type": "int24"},
                    {"name": "tickUpper", "type": "int24"},
                    {"name": "liquidity", "type": "uint128"},
                    {"name": "feeGrowthInside0LastX128", "type": "uint256"},
                    {"name": "feeGrowthInside1LastX128", "type": "uint256"},
                    {"name": "tokensOwed0", "type": "uint128"},
                    {"name": "tokensOwed1", "type": "uint128"}
                ],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "name": "mint",
                "inputs": [{
                    "components": [
                        {"name": "token0", "type": "address"},
                        {"name": "token1", "type": "address"},
                        {"name": "fee", "type": "uint24"},
                        {"name": "tickLower", "type": "int24"},
                        {"name": "tickUpper", "type": "int24"},
                        {"name": "amount0Desired", "type": "uint256"},
                        {"name": "amount1Desired", "type": "uint256"},
                        {"name": "amount0Min", "type": "uint256"},
                        {"name": "amount1Min", "type": "uint256"},
                        {"name": "recipient", "type": "address"},
                        {"name": "deadline", "type": "uint256"}
                    ],
                    "name": "params",
                    "type": "tuple"
                }],
                "outputs": [
                    {"name": "tokenId", "type": "uint256"},
                    {"name": "liquidity", "type": "uint128"},
                    {"name": "amount0", "type": "uint256"},
                    {"name": "amount1", "type": "uint256"}
                ],
                "stateMutability": "payable",
                "type": "function"
            }
        ]
        
        # ERC20 ABI
        self.ABI_ERC20 = [
            {
                "name": "balanceOf",
                "inputs": [{"name": "owner", "type": "address"}],
                "outputs": [{"name": "balance", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "name": "approve",
                "inputs": [
                    {"name": "spender", "type": "address"},
                    {"name": "amount", "type": "uint256"}
                ],
                "outputs": [{"name": "", "type": "bool"}],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]
        
        # Quoter V2 ABI
        self.ABI_QUOTER = [
            {
                "inputs": [
                    {"name": "path", "type": "bytes"},
                    {"name": "amountIn", "type": "uint256"}
                ],
                "name": "quoteExactInput",
                "outputs": [{"name": "amountOut", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]
        
        # SwapRouter ABI
        self.ABI_ROUTER = [
            {
                "name": "exactInputSingle",
                "inputs": [
                    {
                        "components": [
                            {"name": "tokenIn", "type": "address"},
                            {"name": "tokenOut", "type": "address"},
                            {"name": "fee", "type": "uint24"},
                            {"name": "recipient", "type": "address"},
                            {"name": "deadline", "type": "uint256"},
                            {"name": "amountIn", "type": "uint256"},
                            {"name": "amountOutMinimum", "type": "uint256"},
                            {"name": "sqrtPriceLimitX96", "type": "uint160"}
                        ],
                        "name": "params",
                        "type": "tuple"
                    }
                ],
                "outputs": [{"name": "amountOut", "type": "uint256"}],
                "stateMutability": "payable",
                "type": "function"
            }
        ]
        
        # WETH ABI (用于ETH <-> WETH转换)
        self.ABI_WETH = [
            {
                "name": "deposit",
                "inputs": [],
                "outputs": [],
                "stateMutability": "payable",
                "type": "function"
            },
            {
                "name": "withdraw",
                "inputs": [{"name": "wad", "type": "uint256"}],
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "name": "balanceOf",
                "inputs": [{"name": "account", "type": "address"}],
                "outputs": [{"name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]

    # === 基础 ===
    def fetch_balance(self, token=None):
        """获取代币余额"""
        if not self.address:
            print("❌ 未设置钱包地址")
            if token:
                return 0.0
            else:
                return {}
        
        # 单 token 查询
        if token:
            # 支持通过币种名称查询
            if isinstance(token, str) and not token.startswith('0x'):
                # 通过币种名称查询
                formatted_symbol, base, quote, base_address, quote_address = self._norm_symbol(token)
                if base_address:
                    token_address = base_address
                    token_name = base
                else:
                    print(f"❌ 不支持的币种: {token}")
                    return 0.0
            else:
                # 直接使用合约地址
                token_address = token
                token_name = "Unknown"
            
            try:
                erc20 = self.w3.eth.contract(address=token_address, abi=self.ABI_ERC20)
                dec = 6 if token_address == self.USDC else 18
                balance = erc20.functions.balanceOf(self.address).call()
                return float(balance) / (10 ** dec)
            except Exception as e:
                print(f"❌ 获取代币 {token_name} 余额失败: {e}")
                return 0.0
        # 多 token 查询
        else:
            tokens = [self.USDC, self.WETH]
            result = {}
            for t in tokens:
                try:
                    erc20 = self.w3.eth.contract(address=t, abi=self.ABI_ERC20)
                    dec = 6 if t == self.USDC else 18
                    balance = erc20.functions.balanceOf(self.address).call()
                    result[t] = float(balance) / (10 ** dec)
                except Exception as e:
                    print(f"❌ 获取代币 {t} 余额失败: {e}")
                    result[t] = 0.0
            return result

    def get_price_now(self, symbol="USDC-WETH", amount_in=100):
        """获取当前价格"""
        try:
            # 格式化币种名称
            formatted_symbol, base, quote, base_address, quote_address = self._norm_symbol(symbol)
            if not base_address or not quote_address:
                return None, f"不支持的币种对: {symbol}"
            
            quoter = self.w3.eth.contract(address=self.QUOTER_V2, abi=self.ABI_QUOTER)
            # 构建交易路径: base -> quote
            path = Web3.to_bytes(hexstr=base_address[2:] + f"{self.FEE:06x}" + quote_address[2:])
            
            # 根据币种确定精度
            if base == 'USDC':
                amount_in_wei = int(amount_in * 1e6)  # USDC 6位小数
                decimals_in = 6
            else:
                amount_in_wei = int(amount_in * 1e18)  # WETH 18位小数
                decimals_in = 18
            
            out = quoter.functions.quoteExactInput(path, amount_in_wei).call()
            
            # 计算价格
            if quote == 'USDC':
                price = out / 1e6 / (amount_in_wei / (10 ** decimals_in))  # quote是USDC
            else:
                price = out / 1e18 / (amount_in_wei / (10 ** decimals_in))  # quote是WETH
                
            return price, None
        except Exception as e:
            print(f"❌ 获取价格失败: {e}")
            return None, str(e)

    # === 增加流动性 ===
    def add_liquidity(self, amount0=100, amount1=0.05, symbol="USDC-WETH",
                      tick_lower=-887220, tick_upper=887220):
        """添加流动性"""
        if not self.account:
            print("❌ 未设置私钥，无法执行交易")
            return None
            
        try:
            # 格式化币种名称
            formatted_symbol, base, quote, base_address, quote_address = self._norm_symbol(symbol)
            if not base_address or not quote_address:
                print(f"❌ 不支持的币种对: {symbol}")
                return None
            
            pm = self.w3.eth.contract(address=self.POSITION_MANAGER, abi=self.ABI_POSITION_MANAGER)
            
            # 检查余额
            balance = self.fetch_balance()
            if balance.get(base_address, 0) < amount0:
                print(f"❌ {base}余额不足: {balance.get(base_address, 0)} < {amount0}")
                return None
            if balance.get(quote_address, 0) < amount1:
                print(f"❌ {quote}余额不足: {balance.get(quote_address, 0)} < {amount1}")
                return None
            
            # 根据币种确定精度
            decimals0 = 6 if base == 'USDC' else 18
            decimals1 = 6 if quote == 'USDC' else 18
            
            # 构建mint参数
            params = (
                base_address, quote_address, self.FEE, tick_lower, tick_upper,
                int(amount0 * (10 ** decimals0)), int(amount1 * (10 ** decimals1)),
                0, 0, self.address, int(time.time()) + 600
            )
            
            # 获取当前gas价格并稍微提高
            current_gas_price = self.w3.eth.gas_price
            gas_price = int(current_gas_price * 1.2)  # 提高20%确保成功
            
            tx = pm.functions.mint(params).build_transaction({
                "from": self.address,
                "gas": 800000,
                "gasPrice": gas_price,
                "nonce": self.w3.eth.get_transaction_count(self.address)
            })
            
            signed = self.w3.eth.account.sign_transaction(tx, self.account.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            print(f"📥 add_liquidity tx ({formatted_symbol}): {tx_hash.hex()}")
            return tx_hash.hex()
            
        except Exception as e:
            print(f"❌ 添加流动性失败: {e}")
            return None

    # === 查询仓位 ===
    def get_position(self, token_id=None):
        """
        查询流动性仓位。
        - 若 token_id 指定，查询单仓位；
        - 否则返回 self.positions 记录。
        """
        try:
            pm = self.w3.eth.contract(address=self.POSITION_MANAGER, abi=self.ABI_POSITION_MANAGER)
            if token_id:
                data = pm.functions.positions(token_id).call()
                return {
                    "tokenId": token_id,
                    "token0": data[2],
                    "token1": data[3],
                    "fee": data[4],
                    "tickLower": data[5],
                    "tickUpper": data[6],
                    "liquidity": data[7],
                    "tokensOwed0": data[10],
                    "tokensOwed1": data[11]
                }
            else:
                return self.positions
        except Exception as e:
            print(f"❌ 查询仓位失败: {e}")
            return None if token_id else {}

    # === 更新内部仓位记录 ===
    def update_position(self, token_id):
        """更新内部仓位记录"""
        data = self.get_position(token_id)
        if data:
            self.positions[token_id] = data
            print(f"✅ position {token_id} updated: liquidity={data['liquidity']}")
        else:
            print(f"❌ 无法更新仓位 {token_id}")

    # === 示例 swap ===
    # === 下单（swap） ===
    def place_order(self, symbol, side, order_type, size, price=None, **kwargs):
        """
        模拟 CEX 下单接口，底层调用 Uniswap Router。
        side: 'buy' -> base->quote, 'sell' -> quote->base
        """
        if not self.account:
            raise ValueError("未设置私钥，无法签名交易")

        # 格式化币种名称
        formatted_symbol, base, quote, base_address, quote_address = self._norm_symbol(symbol)
        if not base_address or not quote_address:
            return None, f"不支持的币种对: {symbol}"

        # 根据买卖方向确定输入输出代币
        if side.lower() == "buy":
            token_in = base_address
            token_out = quote_address
            token_in_name = base
            token_out_name = quote
        else:  # sell
            token_in = quote_address
            token_out = base_address
            token_in_name = quote
            token_out_name = base

        # 根据代币确定精度
        decimals_in = 6 if token_in_name == 'USDC' else 18
        amount_in = int(size * (10 ** decimals_in))

        try:
            # 检查代币余额
            balance = self.fetch_balance()
            token_balance = balance.get(token_in, 0)
            if token_balance < size:
                return None, f"{token_in_name}余额不足: {token_balance} < {size}"
            
            # Approve router
            erc20 = self.w3.eth.contract(address=token_in, abi=self.ABI_ERC20)
            
            # 获取当前gas价格并稍微提高
            current_gas_price = self.w3.eth.gas_price
            gas_price = int(current_gas_price * 1.2)  # 提高20%确保成功
            
            # 获取nonce
            nonce = self.w3.eth.get_transaction_count(self.address)
            
            approve_tx = erc20.functions.approve(self.ROUTER, amount_in).build_transaction({
                "from": self.address,
                "gas": 100000,
                "gasPrice": gas_price,
                "nonce": nonce
            })
            signed = self.w3.eth.account.sign_transaction(approve_tx, self.account.key)
            approve_tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            print(f"✅ Approve sent ({token_in_name}): {approve_tx_hash.hex()}")
            
            # 等待approve交易确认
            print("⏳ 等待approve交易确认...")
            self._wait_for_transaction(approve_tx_hash)
            
            # Swap
            router = self.w3.eth.contract(address=self.ROUTER, abi=self.ABI_ROUTER)
            params = (token_in, token_out, self.FEE, self.address, int(time.time()) + 600,
                      amount_in, 0, 0)

            # 获取新的nonce和gas价格
            nonce = self.w3.eth.get_transaction_count(self.address)
            current_gas_price = self.w3.eth.gas_price
            gas_price = int(current_gas_price * 1.2)  # 提高20%

            swap_tx = router.functions.exactInputSingle(params).build_transaction({
                "from": self.address,
                "gas": 300000,
                "gasPrice": gas_price,
                "nonce": nonce
            })
            signed_swap = self.w3.eth.account.sign_transaction(swap_tx, self.account.key)
            swap_tx_hash = self.w3.eth.send_raw_transaction(signed_swap.raw_transaction)
            print(f"✅ Swap sent ({formatted_symbol} {side}): {swap_tx_hash.hex()}")
            return swap_tx_hash.hex(), None
            
        except Exception as e:
            print(f"❌ 交易失败: {e}")
            return None, str(e)

    def buy(self, symbol, size, price=None, order_type="market", **kwargs):
        """
        便利的买入函数
        :param symbol: 交易对符号，如 'USDC-WETH' 或 'usdc'
        :param size: 买入数量
        :param price: 价格（对于limit订单）
        :param order_type: 订单类型，'market' 或 'limit'
        :return: (tx_hash, error)
        """
        return self.place_order(
            symbol=symbol,
            side="buy",
            order_type=order_type,
            size=float(size),
            price=price,
            **kwargs,
        )

    def sell(self, symbol, size, price=None, order_type="market", **kwargs):
        """
        便利的卖出函数
        :param symbol: 交易对符号，如 'USDC-WETH' 或 'weth'
        :param size: 卖出数量
        :param price: 价格（对于limit订单）
        :param order_type: 订单类型，'market' 或 'limit'
        :return: (tx_hash, error)
        """
        return self.place_order(
            symbol=symbol,
            side="sell",
            order_type=order_type,
            size=float(size),
            price=price,
            **kwargs,
        )
    
    def _wait_for_transaction(self, tx_hash, timeout=60):
        """等待交易确认"""
        try:
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
            if receipt.status == 1:
                print(f"✅ 交易确认成功: {tx_hash.hex()}")
                return True
            else:
                print(f"❌ 交易失败: {tx_hash.hex()}")
                return False
        except Exception as e:
            print(f"⚠️  等待交易超时: {e}")
            return False

    def _estimate_gas_cost(self, tx):
        """估算交易gas成本"""
        try:
            gas_estimate = self.w3.eth.estimate_gas(tx)
            gas_price = tx.get('gasPrice', self.w3.eth.gas_price)
            cost_wei = gas_estimate * gas_price
            cost_eth = self.w3.from_wei(cost_wei, 'ether')
            return gas_estimate, cost_eth
        except Exception as e:
            print(f"⚠️  Gas估算失败: {e}")
            return 200000, 0.001  # 默认值

    def get_eth_balance(self):
        """获取ETH余额"""
        if not self.address:
            return 0
        try:
            balance = self.w3.eth.get_balance(self.address)
            return self.w3.from_wei(balance, 'ether')
        except Exception as e:
            print(f"❌ 获取ETH余额失败: {e}")
            return 0

    def eth_to_weth(self, amount_eth):
        """将ETH转换为WETH"""
        if not self.account:
            print("❌ 未设置私钥，无法执行交易")
            return None
            
        try:
            # 检查ETH余额
            eth_balance = self.get_eth_balance()
            if eth_balance < amount_eth:
                print(f"❌ ETH余额不足: {eth_balance:.6f} < {amount_eth}")
                return None
            
            # 检查WETH余额
            weth_balance_before = self.fetch_balance().get(self.WETH, 0)
            
            # 创建WETH合约实例
            weth_contract = self.w3.eth.contract(address=self.WETH, abi=self.ABI_WETH)
            
            # 获取gas价格
            current_gas_price = self.w3.eth.gas_price
            gas_price = int(current_gas_price * 1.2)  # 提高20%
            
            # 构建deposit交易
            amount_wei = self.w3.to_wei(amount_eth, 'ether')
            tx = weth_contract.functions.deposit().build_transaction({
                "from": self.address,
                "value": amount_wei,  # 发送ETH
                "gas": 100000,
                "gasPrice": gas_price,
                "nonce": self.w3.eth.get_transaction_count(self.address)
            })
            
            # 签名并发送交易
            signed = self.w3.eth.account.sign_transaction(tx, self.account.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            print(f"🔄 ETH->WETH转换交易已发送: {tx_hash.hex()}")
            
            # 等待交易确认
            self._wait_for_transaction(tx_hash)
            
            # 检查转换结果
            weth_balance_after = self.fetch_balance().get(self.WETH, 0)
            converted_amount = weth_balance_after - weth_balance_before
            
            print(f"✅ ETH->WETH转换成功!")
            print(f"   转换数量: {amount_eth:.6f} ETH -> {converted_amount:.6f} WETH")
            print(f"   当前WETH余额: {weth_balance_after:.6f} WETH")
            
            return tx_hash.hex()
            
        except Exception as e:
            print(f"❌ ETH->WETH转换失败: {e}")
            return None

    def weth_to_eth(self, amount_weth):
        """将WETH转换为ETH"""
        if not self.account:
            print("❌ 未设置私钥，无法执行交易")
            return None
            
        try:
            # 检查WETH余额
            weth_balance = self.fetch_balance().get(self.WETH, 0)
            if weth_balance < amount_weth:
                print(f"❌ WETH余额不足: {weth_balance:.6f} < {amount_weth}")
                return None
            
            # 检查ETH余额
            eth_balance_before = self.get_eth_balance()
            
            # 创建WETH合约实例
            weth_contract = self.w3.eth.contract(address=self.WETH, abi=self.ABI_WETH)
            
            # 获取gas价格
            current_gas_price = self.w3.eth.gas_price
            gas_price = int(current_gas_price * 1.2)  # 提高20%
            
            # 构建withdraw交易
            amount_wei = self.w3.to_wei(amount_weth, 'ether')
            tx = weth_contract.functions.withdraw(amount_wei).build_transaction({
                "from": self.address,
                "gas": 100000,
                "gasPrice": gas_price,
                "nonce": self.w3.eth.get_transaction_count(self.address)
            })
            
            # 签名并发送交易
            signed = self.w3.eth.account.sign_transaction(tx, self.account.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            print(f"🔄 WETH->ETH转换交易已发送: {tx_hash.hex()}")
            
            # 等待交易确认
            self._wait_for_transaction(tx_hash)
            
            # 检查转换结果
            eth_balance_after = self.get_eth_balance()
            converted_amount = eth_balance_after - eth_balance_before
            
            print(f"✅ WETH->ETH转换成功!")
            print(f"   转换数量: {amount_weth:.6f} WETH -> {converted_amount:.6f} ETH")
            print(f"   当前ETH余额: {eth_balance_after:.6f} ETH")
            
            return tx_hash.hex()
            
        except Exception as e:
            print(f"❌ WETH->ETH转换失败: {e}")
            return None


if __name__ == "__main__":
    # 测试代码
    pk = os.getenv("BASE_PRIVATE_KEY")
    if not pk:
        print("⚠️  请设置环境变量 BASE_PRIVATE_KEY")
        print("示例: export BASE_PRIVATE_KEY='your_private_key_here'")
        exit(1)
    
    try:
        base = BaseDriver(pk)
        print("🔗 已连接到Base网络")
        print(f"📍 钱包地址: {base.address}")
        
        # 获取余额
        balance = base.fetch_balance()
        print("💰代币余额:", balance)
        
        # 获取ETH余额
        eth_balance = base.get_eth_balance()
        print(f"💰ETH余额: {eth_balance:.6f} ETH")
        
        # 获取当前gas价格信息
        try:
            gas_price = base.w3.eth.gas_price
            gas_price_gwei = base.w3.from_wei(gas_price, 'gwei')
            print(f"⛽ 当前Gas价格: {gas_price_gwei:.2f} Gwei")
        except Exception as e:
            print(f"⚠️  获取Gas价格失败: {e}")
        
        # 获取价格 - 展示多种格式支持
        print("🪙 价格查询测试:")
        for symbol in ["USDC-WETH", "usdc", "WETH", "weth-usdc"]:
            price, error = base.get_price_now(symbol)
            if price:
                print(f"   {symbol} -> {price:.6f}")
            else:
                print(f"   {symbol} -> 失败: {error}")
        
        # 展示余额查询的通用性
        print("💰 余额查询测试:")
        for token in ["USDC", "WETH", "usdc", "weth"]:
            balance = base.fetch_balance(token)
            print(f"   {token}: {balance:.6f}")
        
        # 示例：添加流动性（注释掉，避免意外执行）
        # base.add_liquidity(amount0=100, amount1=0.05, symbol="USDC-WETH")
        
        # 示例：查询仓位（需要有效的token_id）
        # print(base.get_position(1234))

        # 示例：ETH到WETH转换（如果有ETH余额）
        if eth_balance > 0.01:  # 确保有足够的ETH
            print("🔄 尝试ETH->WETH转换...")
            # 转换0.005 ETH到WETH（保留一些ETH支付gas）
            convert_amount = min(0.005, eth_balance - 0.005)  # 保留0.005 ETH作为gas
            tx_hash = base.eth_to_weth(convert_amount)
            if tx_hash:
                print(f"✅ ETH->WETH转换成功: {tx_hash}")
                
                # 转换成功后，尝试多种格式的交易
                print("🔄 尝试多种格式的交易...")
                for symbol in ["USDC-WETH", "usdc", "WETH"]:
                    print(f"   测试交易对: {symbol}")
                    tx_hash, error = base.sell(symbol, 0.001)  # 卖出0.001
                    if tx_hash:
                        print(f"   ✅ 交易成功: {tx_hash}")
                        break  # 成功一次就够了
                    else:
                        print(f"   ❌ 交易失败: {error}")
            else:
                print("❌ ETH->WETH转换失败")
        else:
            print("⚠️  ETH余额不足，跳过转换测试")
            print(f"💡 提示：需要至少0.01 ETH来进行转换和交易")
        
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
