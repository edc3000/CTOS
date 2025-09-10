from backpack_okex_style import BackpackSpot

# 从 BP_PUBLIC_KEY / BP_SECRET_KEY / BP_WINDOW / BP_PROXY 构造
bp = BackpackSpot.from_env("SOL-USDC")  # 内部自动转 SOL_USDT

# —— 下单 / 查询 ——
oid, err = bp.buy(price=175.66, quantity="0.02", order_type="Limit", time_in_force="IOC")
print("buy:", oid, err)

print("last:", bp.get_price_now())

ids, err = bp.get_open_orders()
print("open:", ids, err)

new_oid, err = bp.amend_order(orderId=oid, price="0.02")
print("amend:", new_oid, err)

rvk, err = bp.revoke_order(order_id=new_oid)
print("revoke:", rvk, err)

pos, err = bp.fetch_position()
print("pos:", pos if not err else err)
