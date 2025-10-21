# Aster DEX Driver

这是CTOS框架的Aster DEX驱动实现，提供与OKX driver相同的接口，适配Aster协议交易。

## 功能特性

- **统一接口**: 与OKX driver保持相同的API接口，确保上层代码可以无缝切换
- **现货交易**: 支持Aster DEX的现货交易功能
- **市场数据**: 提供价格、K线、订单簿等市场数据查询
- **订单管理**: 支持下单、撤单、修改订单等操作
- **账户管理**: 提供余额查询、持仓管理等功能
- **错误处理**: 完善的错误处理和异常管理
- **中文注释**: 详细的中文注释和文档

## 主要方法

### 市场数据
- `get_price_now(symbol)`: 获取当前价格
- `get_orderbook(symbol, level)`: 获取订单簿
- `get_klines(symbol, timeframe, limit)`: 获取K线数据

### 交易操作
- `place_order(symbol, side, order_type, size, price)`: 下单
- `buy(symbol, size, price, order_type)`: 买入订单
- `sell(symbol, size, price, order_type)`: 卖出订单
- `amend_order(order_id, symbol, **kwargs)`: 修改订单
- `revoke_order(order_id)`: 撤销订单
- `cancel_all(symbol, order_ids)`: 撤销所有订单

### 订单查询
- `get_order_status(order_id, symbol)`: 获取订单状态
- `get_open_orders(symbol, onlyOrderId)`: 获取未成交订单

### 账户管理
- `fetch_balance(currency)`: 获取余额
- `get_position(symbol)`: 获取持仓信息
- `close_all_positions(mode, price_offset, symbol, side, is_good)`: 平仓

### 交易所信息
- `symbols(instType)`: 获取交易对列表
- `exchange_limits(symbol, instType)`: 获取交易所限制
- `fees(symbol, instType)`: 获取费率信息

## 使用示例

```python
from ctos.drivers.aster.driver import AsterDriver

# 初始化driver
driver = AsterDriver(account_id=0)

# 获取当前价格
price = driver.get_price_now('ETH-USDT')
print(f"ETH价格: {price}")

# 下单
order_id, error = driver.buy('ETH-USDT', 0.01, 3500.0, 'limit')
if not error:
    print(f"订单已提交: {order_id}")

# 查询订单状态
order_status, error = driver.get_order_status(order_id)
print(f"订单状态: {order_status}")

# 撤销订单
success, error = driver.revoke_order(order_id)
print(f"撤销结果: {success}")

# 获取余额
balance = driver.fetch_balance('USDT')
print(f"USDT余额: {balance}")

# 获取持仓
position, error = driver.get_position('ETH-USDT')
print(f"持仓信息: {position}")
```

## 配置

### 账户配置
在 `configs/account.yaml` 中配置Aster账户信息：

```yaml
accounts:
  aster:
    - name: main
      private_key: "your_private_key_here"
      rpc_url: "https://rpc.aster.xyz"
      chain_id: 1
    - name: sub1
      private_key: "another_private_key"
      rpc_url: "https://rpc.aster.xyz"
      chain_id: 1
```

### 环境变量
也可以通过环境变量配置：

```bash
export ASTER_PRIVATE_KEY="your_private_key_here"
export ASTER_RPC_URL="https://rpc.aster.xyz"
export ASTER_CHAIN_ID="1"
```

## 测试

运行测试文件验证功能：

```bash
cd ctos/drivers/aster
python test_aster_driver.py
```

## 注意事项

1. **现货交易**: Aster是现货DEX，不支持永续合约，因此没有资金费率
2. **模拟实现**: 当前实现包含模拟数据，需要根据实际的Aster SDK进行替换
3. **错误处理**: 所有方法都返回 `(result, error)` 格式，需要检查error字段
4. **符号格式**: 支持 'ETH-USDT'、'ETH/USDT'、'eth' 等多种格式输入

## 与OKX Driver的兼容性

Aster driver完全兼容OKX driver的接口，可以无缝替换：

```python
# 从OKX切换到Aster只需要修改导入
# from ctos.drivers.okx.driver import OkxDriver
from ctos.drivers.aster.driver import AsterDriver

# 其他代码保持不变
driver = AsterDriver(account_id=0)
# ... 使用相同的API
```

## 开发说明

### 添加新功能
1. 在 `AsterClient` 类中添加底层API方法
2. 在 `AsterDriver` 类中添加对应的公开方法
3. 确保返回格式与OKX driver保持一致
4. 添加相应的测试用例

### 错误处理
- 所有API调用都应该包含try-catch
- 返回格式为 `(result, error)`
- 错误信息应该清晰明确

### 文档更新
- 添加新方法时更新README
- 保持中文注释的准确性
- 提供使用示例
