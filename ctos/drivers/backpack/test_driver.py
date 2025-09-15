from driver import *
bp = BackpackDriver()
order_id, err  = bp.place_order('ETH_USDC_PERP', 'bid', 'limit', 0.1, 4500)
# print(order_id, err)
# print(bp.fees())
# print(bp.fetch_balance())
print(bp.get_open_orders(symbol=None))
# order_id, err = bp.amend_order(order_id=order_id, symbol='ETH_USDC_PERP', price=4488)
# print(bp.get_order_status(symbol='ETH_USDC_PERP', order_id=order_id))

print(bp.revoke_order(order_id=order_id, symbol='ETH_USDC_PERP'))
# print(bp.get_posistion('BTC_USDC_PERP'))
