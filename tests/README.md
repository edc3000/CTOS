# Test content of okx driver - Round 1st
(trade) zzb@xiuos7:~/Quantify/ctos$ python tests/test_okx_driver.py 
没这个pyfiglet包
<ctos.drivers.okx.driver.OkxDriver object at 0x7f499a59b8e0>
[TEST] before call: get_price_now
ETH-USDT-SWAP eth
[TEST] after call: get_price_now -> 4335.28
[TEST] before call: get_orderbook
[TEST] after call: get_orderbook -> {'symbol': 'ETH-USDT-SWAP', 'bids': [], 'asks': []}
[TEST] before call: get_klines
[TEST] after call: get_klines -> (       trade_date     open     high      low    close        vol1               vol
0   1756483200000  4314.09  4338.59  4292.67  4335.67   79016.157   340748057.39255
1   1756479600000  4281.32     4347   4280.4  4314.09  263684.132  1139692681.00486
2   1756476000000  4329.57  4354.56  4260.51  4281.33  617783.493  2653562949.61942
3   1756472400000  4404.99     4411  4311.29  4329.57  382204.574  1663654765.60279
4   1756468800000  4345.15  4453.05  4345.15     4405  429307.189  1889717155.52079
5   1756465200000     4345  4357.86  4331.22  4345.16   80321.424   348847293.25295
6   1756461600000  4336.82  4361.73   4333.1     4345  146055.366   635024231.76583
7   1756458000000  4334.56  4344.64  4318.01  4336.81   207498.28   898809908.35286
8   1756454400000     4380     4397  4327.62  4334.55   277947.33  1211963597.38945
9   1756450800000  4455.13  4455.14     4365     4380  401226.394  1765115562.78349
10  1756447200000  4478.75  4486.09  4443.66  4455.14   156545.41   698187185.88816
11  1756443600000   4475.5  4483.94     4462  4478.74   59908.442   267940365.94854
12  1756440000000  4487.84   4495.8  4466.89   4475.5   64624.882   289686862.74827
13  1756436400000  4478.95   4504.1   4465.8  4487.84   83669.089   375536453.14776
14  1756432800000  4454.81  4494.44  4448.64  4478.95  108531.503   485780655.46036
15  1756429200000  4480.69  4489.42  4432.75  4454.82  153602.481   684616270.19099
16  1756425600000  4509.16  4516.37  4467.44  4480.69  104098.144    467378917.7729
17  1756422000000  4504.06  4513.67     4492  4509.15   65786.251   296168248.24097
18  1756418400000  4486.54  4514.56     4486  4504.06   60243.094   271236478.17728
19  1756414800000  4457.19  4489.99  4455.19  4486.55   59638.432   266981531.75461, None)
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
[TEST] after call: get_posistion -> ({'code': '0', 'data': [{'adl': '1', 'availPos': '', 'avgPx': '4409.0689789029535865', 'baseBal': '', 'baseBorrowed': '', 'baseInterest': '', 'bePx': '5299.750118738131', 'bizRefId': '', 'bizRefType': '', 'cTime': '1756289161316', 'ccy': 'USDT', 'clSpotInUseAmt': '', 'closeOrderAlgo': [], 'deltaBS': '', 'deltaPA': '', 'fee': '-1.696101094', 'fundingFee': '-0.7641384003009353', 'gammaBS': '', 'gammaPA': '', 'idxPx': '4338.56', 'imr': '17.345280000000002', 'instId': 'ETH-USDT-SWAP', 'instType': 'SWAP', 'interest': '', 'last': '4336.57', 'lever': '20', 'liab': '', 'liabCcy': '', 'liqPenalty': '0', 'liqPx': '', 'margin': '', 'markPx': '4336.32', 'maxSpotInUseAmt': '', 'mgnMode': 'cross', 'mgnRatio': '105.66150310214191', 'mmr': '1.3876224000000001', 'nonSettleAvgPx': '', 'notionalUsd': '346.94029056000005', 'optVal': '', 'pendingCloseOrdLiabVal': '', 'pnl': '-68.58226168776372', 'pos': '0.8', 'posCcy': '', 'posId': '2009134310876151808', 'posSide': 'net', 'quoteBal': '', 'quoteBorrowed': '', 'quoteInterest': '', 'realizedPnl': '-71.04250118206465', 'settledPnl': '', 'spotInUseAmt': '', 'spotInUseCcy': '', 'thetaBS': '', 'thetaPA': '', 'tradeId': '2479481357', 'uTime': '1756483201330', 'upl': '-5.819918312236332', 'uplLastPx': '-5.799918312236333', 'uplRatio': '-0.3299970095775429', 'uplRatioLastPx': '-0.3288629833185008', 'usdPx': '1.0001', 'vegaBS': '', 'vegaPA': ''}], 'msg': ''}, None)
[TEST] before call: symbols
[TEST] after call: symbols -> ['BTC-USDT', 'ETH-USDT', 'SOL-USDT']
[TEST] before call: exchange_limits
[TEST] after call: exchange_limits -> {'price_scale': 1e-08, 'size_scale': 1e-08}
[TEST] before call: fees
[TEST] after call: fees -> {'maker': None, 'taker': None}