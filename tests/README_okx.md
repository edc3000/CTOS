<ctos.drivers.okx.driver.OkxDriver object at 0x7fe8668ff8e0>

[TEST] before call: get_price_now
ETH-USDT-SWAP eth

[TEST] after call: get_price_now -> 4377.81

[TEST] before call: get_orderbook

[TEST] after call: get_orderbook -> {'symbol': 'ETH-USDT-SWAP', 'bids': [], 'asks': []}

[TEST] before call: get_klines

[TEST] after call: get_klines -> (       trade_date     open     high      low    close        vol1               vol
0   1757520000000  4403.65  4408.12  4360.86  4377.81  188500.786   825362042.47118
1   1757516400000  4399.78   4423.6  4395.04  4403.66  113777.037   501495394.88369
2   1757512800000  4416.93  4453.74  4396.65  4399.79   300133.95  1328412418.26251
3   1757509200000  4369.95  4438.37  4355.13  4416.93  447514.828  1968130112.48219
4   1757505600000  4329.98  4393.96  4328.33  4369.95  435246.301  1900430795.15771
5   1757502000000  4325.53  4331.56     4320  4329.97   40557.758   175492456.80997
6   1757498400000  4323.26  4331.86  4315.78  4325.52   53629.997   231968650.74817
7   1757494800000  4330.12     4331  4307.05  4323.27   84566.782   365189340.14641
8   1757491200000  4328.24  4332.89     4322  4330.11   79573.664     344356970.023
9   1757487600000  4312.23     4333     4311  4328.24   97229.194   420479239.22667
10  1757484000000  4307.84     4318  4296.62  4312.22   72944.942   314127589.46093
11  1757480400000  4311.79  4318.39  4293.39  4307.94   76965.076   331449620.99128
12  1757476800000  4319.95  4319.95  4307.11  4311.79   33723.355   145438731.02091
13  1757473200000  4316.92   4323.5  4306.57  4319.96   55966.507   241505123.27415
14  1757469600000  4302.32  4326.79  4302.31  4316.92  108444.583   468162249.23234
15  1757466000000  4285.28  4313.99     4285  4302.31   69535.248   298953777.69043
16  1757462400000  4309.55  4314.89   4284.6  4285.28   76937.863   330638120.77208
17  1757458800000   4318.2  4318.64     4302  4309.56   45432.402   195801794.59115
18  1757455200000  4301.89   4318.3  4298.39  4318.19   42570.634   183525366.19398
19  1757451600000  4304.43  4319.94  4292.63   4301.9    59428.94   255997230.12748, None)

[TEST] before call: place_order
ETH-USDT-SWAP eth

[TEST] after call: place_order -> ('2852827355428593664', None)

[TEST] before call: amend_order
ETH-USDT-SWAP eth

[TEST] after call: amend_order -> ('2852827355428593664', None)

[TEST] before call: get_order_status

[TEST] after call: get_order_status -> ({'code': '0', 'data': [{'accFillSz': '0', 'algoClOrdId': '', 'algoId': '', 'attachAlgoClOrdId': '', 'attachAlgoOrds': [], 'avgPx': '', 'cTime': '1757523280562', 'cancelSource': '', 'cancelSourceReason': '', 'category': 'normal', 'ccy': '', 'clOrdId': '', 'fee': '0', 'feeCcy': 'USDT', 'fillPx': '', 'fillSz': '0', 'fillTime': '', 'instId': 'ETH-USDT-SWAP', 'instType': 'SWAP', 'isTpLimit': 'false', 'lever': '20', 'linkedAlgoOrd': {'algoId': ''}, 'ordId': '2852827355428593664', 'ordType': 'limit', 'pnl': '0', 'posSide': 'net', 'px': '3502.25', 'pxType': '', 'pxUsd': '', 'pxVol': '', 'quickMgnType': '', 'rebate': '0', 'rebateCcy': 'USDT', 'reduceOnly': 'false', 'side': 'buy', 'slOrdPx': '', 'slTriggerPx': '', 'slTriggerPxType': '', 'source': '', 'state': 'live', 'stpId': '', 'stpMode': 'cancel_maker', 'sz': '0.01', 'tag': '', 'tdMode': 'cross', 'tgtCcy': '', 'tpOrdPx': '', 'tpTriggerPx': '', 'tpTriggerPxType': '', 'tradeId': '', 'tradeQuoteCcy': '', 'uTime': '1757523282478'}], 'msg': ''}, None)

[TEST] before call: get_open_orders

[TEST] after call: get_open_orders -> (['2852827355428593664'], None)

[TEST] before call: revoke_order

[TEST] after call: revoke_order -> ('2852827355428593664', None)

[TEST] before call: cancel_all (no symbol)

[TEST] after call: cancel_all (no symbol) raised: 'NoneType' object is not iterable

[TEST] before call: cancel_all (with symbol)

[TEST] after call: cancel_all (with symbol) raised: 'NoneType' object is not iterable

[TEST] before call: fetch_balance

[TEST] after call: fetch_balance -> 3097.7631607182693

[TEST] before call: get_posistion

[TEST] after call: get_posistion -> ({'code': '0', 'data': [{'adl': '1', 'availPos': '', 'avgPx': '4296.5404560905112562', 'baseBal': '', 'baseBorrowed': '', 'baseInterest': '', 'bePx': '4298.679275879169', 'bizRefId': '', 'bizRefType': '', 'cTime': '1757055993924', 'ccy': 'USDT', 'clSpotInUseAmt': '', 'closeOrderAlgo': [], 'deltaBS': '', 'deltaPA': '', 'fee': '-1.899914526', 'fundingFee': '-1.889476463759645', 'gammaBS': '', 'gammaPA': '', 'idxPx': '4379.6', 'imr': '99.6083725', 'instId': 'ETH-USDT-SWAP', 'instType': 'SWAP', 'interest': '', 'last': '4378.79', 'lever': '20', 'liab': '', 'liabCcy': '', 'liqPenalty': '0', 'liqPx': '', 'margin': '', 'markPx': '4378.39', 'maxSpotInUseAmt': '', 'mgnMode': 'cross', 'mgnRatio': '9.760092122636376', 'mmr': '7.968669800000001', 'nonSettleAvgPx': '', 'notionalUsd': '1992.5061184665', 'optVal': '', 'pendingCloseOrdLiabVal': '', 'pnl': '3.794177521182621', 'pos': '4.55', 'posCcy': '', 'posId': '2009134310876151808', 'posSide': 'net', 'quoteBal': '', 'quoteBorrowed': '', 'quoteInterest': '', 'realizedPnl': '0.0047865314229759', 'settledPnl': '', 'spotInUseAmt': '', 'spotInUseCcy': '', 'thetaBS': '', 'thetaPA': '', 'tradeId': '2519886522', 'uTime': '1757520000573', 'upl': '37.24154247881773', 'uplLastPx': '37.42354247881756', 'uplRatio': '0.3810020864273023', 'uplRatioLastPx': '0.3828640495768987', 'usdPx': '1.00017', 'vegaBS': '', 'vegaPA': ''}], 'msg': ''}, None)

[TEST] before call: symbols

[TEST] after call: symbols -> ['BTC-USDT', 'ETH-USDT', 'SOL-USDT']

[TEST] before call: exchange_limits

[TEST] after call: exchange_limits -> {'price_scale': 1e-08, 'size_scale': 1e-08}

[TEST] before call: fees

[TEST] after call: fees raised: too many values to unpack (expected 2)