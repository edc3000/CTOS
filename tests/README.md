````markdown
# Test content of okx driver - Round 1st

运行测试：
```bash
(trade) zzb@xiuos7:~/Quantify/ctos$ python tests/test_okx_driver.py
````

---

## 测试输出

```
没这个pyfiglet包
<ctos.drivers.okx.driver.OkxDriver object at 0x7f499a59b8e0>

[TEST] before call: get_price_now
ETH-USDT-SWAP eth
[TEST] after call: get_price_now -> 4335.28

[TEST] before call: get_orderbook
[TEST] after call: get_orderbook -> {'symbol': 'ETH-USDT-SWAP', 'bids': [], 'asks': []}

[TEST] before call: get_klines
[TEST] after call: get_klines -> (
       trade_date     open     high      low    close        vol1               vol
0   1756483200000  4314.09  4338.59  4292.67  4335.67   79016.157   340748057.39255
1   1756479600000  4281.32     4347   4280.4  4314.09  263684.132  1139692681.00486
...
19  1756414800000  4457.19  4489.99  4455.19  4486.55   59638.432   266981531.75461, None
)

[TEST] before call: place_order
ETH-USDT-SWAP eth
[TEST] after call: place_order -> ('2817957051212668928', None)

[TEST] before call: amend_order
ETH-USDT-SWAP eth
[TEST] after call: amend_order raised: OkexSpot.amend_order() got an unexpected keyword argument 'order_id'

[TEST] before call: get_order_status
[TEST] after call: get_order_status raised: 'OkexSpot' object has no attribute 'cancel_order'

[TEST] before call: get_open_orders
[TEST] after call: get_open_orders -> (['2817957051212668928', '2817952366846189568'], None)

[TEST] before call: revoke_order
[TEST] after call: revoke_order -> ('2817957051212668928', None)

[TEST] before call: cancel_all (no symbol)
[TEST] after call: cancel_all (no symbol) raised: OkexSpot.revoke_orders() got an unexpected keyword argument 'symbol'

[TEST] before call: cancel_all (with symbol)
[TEST] after call: cancel_all (with symbol) raised: OkexSpot.revoke_orders() got an unexpected keyword argument 'symbol'

[TEST] before call: fetch_balance
[TEST] after call: fetch_balance -> 3582.672907635655

[TEST] before call: get_posistion
[TEST] after call: get_posistion -> ({...}, None)

[TEST] before call: symbols
[TEST] after call: symbols -> ['BTC-USDT', 'ETH-USDT', 'SOL-USDT']

[TEST] before call: exchange_limits
[TEST] after call: exchange_limits -> {'price_scale': 1e-08, 'size_scale': 1e-08}

[TEST] before call: fees
[TEST] after call: fees -> {'maker': None, 'taker': None}
```
