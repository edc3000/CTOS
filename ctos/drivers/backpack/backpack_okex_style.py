# backpack_spot.py
# -*- coding: utf-8 -*-
"""
BackpackSpot：基于 bpx.Account 的 OKX 风格适配器
- 依赖：bpx.base.base_account.BaseAccount, bpx.account.Account, bpx.http_client.SyncHttpClient
- 环境变量（有 BP_ 前缀）：
    BP_PUBLIC_KEY   : Base64 公钥（verifying key）
    BP_SECRET_KEY   : Base64 私钥（ed25519）
    BP_WINDOW       : (可选) 签名窗口，默认 10000 ms
    BP_PROXY        : (可选) 形如 http://host:port 或 socks5://host:port

- 提供的方法（与 okex.py 常用接口对齐）：
    buy(price, quantity, order_type='limit', time_in_force='GTC', client_id=None, reduce_only=None, soft=False)
    sell(price, quantity, order_type='limit', time_in_force='GTC', client_id=None, reduce_only=None, soft=False)
    revoke_order(order_id=None, client_id=None) -> (id, err)
    amend_order(orderId=None, clientId=None, price=None, quantity=None) -> (new_order_id, err)
    get_price_now(symbol: str | None = None) -> float
    get_open_orders() -> (List[str], err)
    fetch_position() -> (Any, err)
    get_posistion() -> alias of fetch_position

注意：
- amend_order：Backpack 无直接“改单”接口，采用“查 -> 撤 -> 重新下”的等价实现。
- 所有真实网络请求处均有「# 网络请求」注释。
"""
from __future__ import annotations
import os
from typing import Optional, Tuple, List, Dict, Any

from bpx.account import Account
from bpx.http_client.sync_http_client import SyncHttpClient
from bpx.constants.enums import (
    OrderTypeType, OrderTypeEnum,
    TimeInForceType, TimeInForceEnum,
)

# ----------------- 小工具：符号与类型映射 -----------------

def _okx_to_bpx_symbol(sym: str) -> str:
    """
    OKX 风格 -> Backpack 风格：
      ETH-USDT(-SWAP)  => ETH_USDT(_PERP)
    """
    s = sym.replace("-", "_").upper()
    if s.endswith("_SWAP"):
        s = s[:-5] + "_PERP"
    return s

def _to_order_type(v) -> str:
    """
    归一化订单类型为 'Limit' 或 'Market'（字符串）。
    允许输入：字符串 / Enum-like（带 .name/.value 的对象）/ 其他可转字符串对象。
    """
    if v is None:
        return "Limit"

    # 1) 先尝试用字符串规则判断
    try:
        s = str(v).strip()
    except Exception:
        return "Limit"

    s_lower = s.lower()
    if "limit" in s_lower or s_lower.startswith("l"):
        return "Limit"
    if "market" in s_lower or s_lower.startswith("m"):
        return "Market"

    # 2) 兼容 Enum-like：优先读取 .name / .value 再次判断
    name = getattr(v, "name", None)
    value = getattr(v, "value", None)
    for cand in (name, value):
        if isinstance(cand, str):
            c = cand.strip().lower()
            if "limit" in c or c.startswith("l"):
                return "Limit"
            if "market" in c or c.startswith("m"):
                return "Market"

    # 3) 兜底
    return "Limit"

def _to_tif(v) -> str:
    """
    归一化 TIF 为 'GTC'/'IOC'/'FOK'/'PostOnly' 字符串。
    """
    if v is None:
        return "GTC"
    try:
        s = str(v).strip()
    except Exception:
        return "GTC"

    s_up = s.upper()
    if s_up in ("GTC", "IOC", "FOK"):
        return s_up
    # 兼容写法：POST_ONLY / POSTONLY / postonly
    if s_up.replace("-", "").replace("_", "") in ("POSTONLY", "POSTONLYTIF"):
        return "PostOnly"
    # 兼容 Enum-like
    name = getattr(v, "name", None)
    value = getattr(v, "value", None)
    for cand in (name, value):
        if isinstance(cand, str):
            cu = cand.strip().upper()
            if cu in ("GTC", "IOC", "FOK"):
                return cu
            if cu.replace("-", "").replace("_", "") == "POSTONLY":
                return "PostOnly"
    return "GTC"


def _parse_proxy(p: Optional[str]) -> Optional[dict]:
    if not p:
        return None
    # SyncHttpClient 走 requests 兼容形式
    return {"http": p, "https": p}

# ----------------- 主类 -----------------

class BackpackSpot:
    """
    适配器：对外暴露 OKX 风格方法，内部复用 bpx.Account（含签名与 http 客户端）
    """
    def __init__(
        self,
        symbol: str,
        public_key: str,
        secret_key: str,
        window: int = 10000,
        proxy: Optional[str] = None,
        debug: bool = False,
        http_client: Optional[SyncHttpClient] = None,
        host: Optional[str] = None,  # ✅ 新增
    ) -> None:
        self.symbol_okx = symbol.upper()                 # 例如 ETH-USDT / ETH-USDT-SWAP
        self.symbol_bpx = _okx_to_bpx_symbol(symbol)     # 例如 ETH_USDT / ETH_USDT_PERP
        self.window = int(window)

        client = http_client or SyncHttpClient()
        # 代理（如需）：http://host:port / socks5://host:port
        client.proxies = _parse_proxy(proxy)
        self.host = (host or os.getenv("BP_HOST") or "https://api.backpack.exchange").rstrip("/")  # ✅ 基础 URL

        # 真实账户客户端，所有私有请求/签名都走此处
        # 网络请求：所有 account.* 调用都会触发真实 HTTP
        self.account = Account(
            public_key=public_key,
            secret_key=secret_key,
            window=self.window,
            proxy=client.proxies,
            debug=debug,
            default_http_client=client,
        )

        # 复用 http_client 做公共请求（如 ticker）
        self._http = client

    # ----------------- 行情 -----------------

    def get_price_now(self, symbol: Optional[str] = None) -> float:
        """
        获取最新价（float）
        - symbol 可传 OKX 风格；默认使用初始化的交易对
        - 使用公开行情：GET /api/v1/ticker?symbol=...
        """
        sym = _okx_to_bpx_symbol(symbol) if symbol else self.symbol_bpx
        # 网络请求：公开端点，无需鉴权
        data = self._http.get(
            url=f"{self.host}/api/v1/ticker",  # ✅ 改成绝对路径
            params={"symbol": sym},
        )
        # Backpack Ticker 字段名：lastPrice
        try:
            return float(data["lastPrice"])
        except Exception as e:
            raise RuntimeError(f"ticker 响应异常: {data}") from e

    # ----------------- 下单/撤单/改单 -----------------

    def buy(
        self,
        price: str | float,
        quantity: str | float,
        order_type: str | OrderTypeType | OrderTypeEnum = "LIMIT",
        time_in_force: str | TimeInForceType | TimeInForceEnum = "GTC",
        client_id: Optional[int] = None,
        reduce_only: Optional[bool] = None,
        soft: bool = False,
    ) -> Tuple[Optional[str], Optional[dict]]:
        """按价格/数量买入；返回 (order_id, err)"""
        return self._place(
            side="Bid",
            price=price,
            quantity=quantity,
            order_type=order_type,
            time_in_force=time_in_force,
            client_id=client_id,
            reduce_only=reduce_only,
            soft=soft,
        )

    def sell(
        self,
        price: str | float,
        quantity: str | float,
        order_type: str | OrderTypeType | OrderTypeEnum = "limit",
        time_in_force: str | TimeInForceType | TimeInForceEnum = "GTC",
        client_id: Optional[int] = None,
        reduce_only: Optional[bool] = None,
        soft: bool = False,
    ) -> Tuple[Optional[str], Optional[dict]]:
        """按价格/数量卖出；返回 (order_id, err)"""
        return self._place(
            side="Ask",
            price=price,
            quantity=quantity,
            order_type=order_type,
            time_in_force=time_in_force,
            client_id=client_id,
            reduce_only=reduce_only,
            soft=soft,
        )

    def _place(
        self,
        side: str,
        price: str | float,
        quantity: str | float,
        order_type: str | OrderTypeType | OrderTypeEnum,
        time_in_force: str | TimeInForceType | TimeInForceEnum,
        client_id: Optional[int],
        reduce_only: Optional[bool],
        soft: bool,
    ) -> Tuple[Optional[str], Optional[dict]]:
        """
        下单统一实现；内部直接调用 bpx.Account.execute_order
        """
        ot = _to_order_type(order_type)
        tif = _to_tif(time_in_force)

        if soft:
            # 不发真实网络请求
            print(f"📦 (SOFT) {side} {quantity} {self.symbol_bpx} @ {price} "
                  f"type={ot} tif={tif} reduce_only={reduce_only} client_id={client_id}")
            return "soft-simulated", None

        # 网络请求：私有 POST /api/v1/order（由 Account 封装）
        try:
            od = self.account.execute_order(
                symbol=self.symbol_bpx,
                side=side,                            # "Bid"/"Ask"
                order_type=ot,                        # OrderTypeType
                time_in_force=tif,                    # TimeInForceType
                quantity=str(quantity),
            )
            if ot.lower() == 'limit':
                # 限价需要填 price
                od = self.account.execute_order(
                    symbol=self.symbol_bpx,
                    side=side,
                    order_type='Limit',
                    time_in_force=tif,
                    quantity=str(quantity),
                    price=str(price),
                    reduce_only=reduce_only,
                    client_id=client_id,
                )
            else:
                # 市价忽略 price；如需按 quote 数量下单，可改用 quote_quantity
                pass

            # 兼容返回结构
            order_id = od.get("id") if isinstance(od, dict) else None
            return order_id, None
        except Exception as e:
            return None, {"msg": f"execute_order failed: {e}"}

    def revoke_order(
        self,
        order_id: Optional[str] = None,
        client_id: Optional[int] = None,
    ) -> Tuple[Optional[str | int], Optional[dict]]:
        """
        撤单（单笔）；返回 (order_id 或 client_id, err)
        """
        if not order_id and client_id is None:
            return None, {"msg": "revoke_order 需要 order_id 或 client_id 至少一个"}
        # 网络请求：私有 DELETE /api/v1/order（由 Account 封装）
        try:
            _ = self.account.cancel_order(
                symbol=self.symbol_bpx,
                order_id=order_id,
                client_id=client_id,
            )
            return (order_id or client_id), None
        except Exception as e:
            return (order_id or client_id), {"msg": f"cancel_order failed: {e}"}

    def amend_order(
        self,
        orderId: Optional[str] = None,
        clientId: Optional[int] = None,
        price: Optional[str | float] = None,
        quantity: Optional[str | float] = None,
    ) -> Tuple[Optional[str], Optional[dict]]:
        """
        等价“改单”：查 -> 撤 -> 以新参数重下；返回 (new_order_id, err)

        注意：真实网络会产生 2~3 次请求：
          1) GET /api/v1/order   （account.get_open_order）
          2) DELETE /api/v1/order（account.cancel_order）
          3) POST /api/v1/order  （account.execute_order）
        """
        if not orderId and clientId is None:
            return None, {"msg": "amend_order 需要 orderId 或 clientId 至少一个"}

        # 1) 查原单
        try:
            # 网络请求
            old = self.account.get_open_order(
                symbol=self.symbol_bpx,
                order_id=orderId,
                client_id=clientId,
            )
            if not old or (isinstance(old, dict) and old.get("message") == "Order not found"):
                return None, {"msg": "原订单不存在或已完成"}
        except Exception as e:
            return None, {"msg": f"get_open_order failed: {e}"}

        # 2) 撤
        _, err = self.revoke_order(order_id=orderId, client_id=clientId)
        if err:
            return None, err

        # 3) 重下（沿用旧 side/type/TIF，替换价格/数量）
        side = old.get("side", "Bid")
        ot = old.get("orderType", 'Limit')
        tif = old.get("timeInForce", 'IOC')

        new_price = str(price) if price is not None else old.get("price")
        new_qty   = str(quantity) if quantity is not None else old.get("quantity")

        return self._place(
            side=side,
            price=new_price,
            quantity=new_qty,
            order_type=ot,
            time_in_force=tif,
            client_id=None,
            reduce_only=old.get("reduceOnly"),
            soft=False,
        )

    # ----------------- 查询 -----------------

    def get_open_orders(self) -> Tuple[Optional[List[str]], Optional[dict]]:
        """
        获取当前未完成订单 ID 列表；返回 (ids, err)
        """
        try:
            # 网络请求：GET /api/v1/orders（account.get_open_orders 封装）
            data = self.account.get_open_orders(symbol=self.symbol_bpx)
            ids = [o["orderId"] for o in data] if isinstance(data, list) else []
            return ids, None
        except Exception as e:
            return None, {"msg": f"get_open_orders failed: {e}"}

    def fetch_position(self) -> Tuple[Any, Optional[dict]]:
        """
        获取持仓信息（永续/杠杆）；返回 (data, err)
        说明：若是纯现货对，可能为空。
        """
        try:
            # 网络请求：Futures positions（account.get_open_positions 封装）
            pos = self.account.get_open_positions()
            return pos, None
        except Exception as e:
            return None, {"msg": f"get_open_positions failed: {e}"}

    # 与历史项目保持一致的别名（很多老代码拼写成 posistion）
    def get_posistion(self) -> Tuple[Any, Optional[dict]]:
        return self.fetch_position()

    # ----------------- 工厂：从 BP_ 环境变量读取 -----------------

    @classmethod
    def from_env(cls, symbol: str, debug: bool = False) -> "BackpackSpot":
        pub = os.getenv("BP_PUBLIC_KEY") or ""
        sec = os.getenv("BP_SECRET_KEY") or ""
        if not pub or not sec:
            raise RuntimeError("请设置 BP_PUBLIC_KEY / BP_SECRET_KEY 环境变量。")
        window = int(os.getenv("BP_WINDOW", "10000"))
        proxy  = os.getenv("BP_PROXY")  # e.g. http://127.0.0.1:7890
        return cls(
            symbol=symbol,
            public_key=pub,
            secret_key=sec,
            window=window,
            proxy=proxy,
            debug=debug,
        )
