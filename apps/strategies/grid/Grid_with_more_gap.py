#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import time
import json
from pathlib import Path
from datetime import datetime, timedelta


def add_project_paths(project_name="ctos", subpackages=None):
    """
    自动查找项目根目录，并将其及常见子包路径添加到 sys.path。
    :param project_name: 项目根目录标识（默认 'ctos'）
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = None
    # 向上回溯，找到项目根目录
    path = current_dir
    while path != os.path.dirname(path):  # 一直回溯到根目录
        if os.path.basename(path) == project_name or os.path.exists(os.path.join(path, ".git")):
            project_root = path
            break
        path = os.path.dirname(path)
    if not project_root:
        raise RuntimeError(f"未找到项目根目录（包含 {project_name} 或 .git）")
    # 添加根目录
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    return project_root
# 执行路径添加
PROJECT_ROOT = add_project_paths()
print('PROJECT_ROOT: ', PROJECT_ROOT, 'CURRENT_DIR: ', os.path.dirname(os.path.abspath(__file__)))


from ctos.drivers.backpack.util import align_decimal_places, round_dynamic, round_to_two_digits, rate_price2order, cal_amount, BeijingTime
from ctos.core.runtime.ExecutionEngine import pick_exchange


def get_GridPositions_storage_path(exchange: str, account: int) -> str:
    """获取GridPositions存储文件路径（统一放到 GridPositions 文件夹下）"""
    logging_dir = os.path.dirname(os.path.abspath(__file__))
    default_strategy = os.path.splitext(os.path.basename(__file__))[0].upper()
    folder = os.path.join(logging_dir, "GridPositions")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f'{exchange}_Account{account}_{default_strategy}_GridPositions.json')

def save_GridPositions(GridPositions: dict, exchange: str, account: int) -> None:
    """保存GridPositions到本地文件"""
    try:
        storage_path = get_GridPositions_storage_path(exchange, account)
        data = {
            'timestamp': datetime.now().isoformat(),
            'exchange': exchange,
            'GridPositions': GridPositions
        }
        with open(storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\r ✓ 持仓数据已保存到: {storage_path}", end='')
    except Exception as e:
        print(f"\r ✗ 保存持仓数据失败: {e}", end='')

def load_GridPositions(exchange: str, account: int) -> tuple[dict, bool]:
    """
    从本地文件加载GridPositions
    返回: (GridPositions_dict, is_valid)
    如果文件不存在或超过1小时，返回空字典和False
    """
    try:
        storage_path = get_GridPositions_storage_path(exchange, account)
        if not os.path.exists(storage_path):
            return {}, False
        
        with open(storage_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 检查时间戳
        saved_time = datetime.fromisoformat(data['timestamp'])
        current_time = datetime.now()
        time_diff = current_time - saved_time
        
        # 如果超过1小时，返回无效
        if time_diff > timedelta(hours=6):
            print(f"⚠ 持仓数据已过期 ({time_diff}), 将重新获取")
            return {}, False
        
        # 检查交易所是否匹配
        if data.get('exchange') != exchange:
            print(f"⚠ 交易所不匹配 (文件: {data.get('exchange')}, 当前: {exchange}), 将重新获取")
            return {}, False
        
        print(f"✓ 从本地加载持仓数据 (保存时间: {saved_time.strftime('%Y-%m-%d %H:%M:%S')})")
        return data.get('GridPositions', {}), True
        
    except Exception as e:
        print(f"✗ 加载持仓数据失败: {e}")
        return {}, False



def get_all_GridPositions(engine, exchange: str, use_cache: bool = True):
    """
    获取所有持仓，支持本地缓存
    返回 {symbol: {baseline_price, entryPrice, side, size, buy_order_id, sell_order_id}} 的字典
    """
    # 尝试从本地加载
    if use_cache:
        cached_GridPositions, is_valid = load_GridPositions(exchange, engine.account)
        if is_valid and cached_GridPositions:
            return cached_GridPositions
    # 从API获取最新持仓
    GridPositions = {}
    try:
        print("正在从API获取最新持仓数据...")
        unified, err = engine.cex_driver.get_position(symbol=None, keep_origin=False)
        if err:
            print("获取持仓失败:", err)
            return {}

        if isinstance(unified, list):
            for pos in unified:
                sym = pos["symbol"]
                size = float(pos["quantity"])
                entry = float(pos["entryPrice"] or 0.0)
                mark = float(pos["markPrice"] or 0.0)
                side = pos["side"]
                pnlUnrealized = float(pos["pnlUnrealized"] or 0.0)
                if size > 0:
                    GridPositions[sym] = {
                        "baseline_price": mark,
                        "avg_cost": entry,
                        "size": size,
                        "side": side,
                        'pnlUnrealized': pnlUnrealized,
                        "buy_order_id": None,  # 买单订单ID
                        "sell_order_id": None,  # 卖单订单ID
                    }
        
        # 保存到本地
        if GridPositions:
            save_GridPositions(GridPositions, exchange, engine.account)
            
    except Exception as e:
        print("get_all_GridPositions 异常:", e)
    return GridPositions

def manage_grid_orders(engine, sym, data, open_orders, price_precision, size_precision, base_amount, config):
    """
    管理网格订单逻辑
    1. 检查买单和卖单是否在open_orders中
    2. 如果都不在，则下新订单
    3. 如果只有一个消失，则处理成交逻辑
    4. 如果两个都在，则等待
    """
    buy_order_id = data.get("buy_order_id")
    sell_order_id = data.get("sell_order_id")
    baseline_price = data["baseline_price"]
    # 检查订单是否存在
    buy_exists = buy_order_id and buy_order_id in open_orders
    sell_exists = sell_order_id and sell_order_id in open_orders
    
    # 计算目标价格
    buy_price = align_decimal_places(price_precision, baseline_price * config["buy_grid_step"])
    sell_price = align_decimal_places(price_precision, baseline_price * config["sell_grid_step"])
    
    # 情况1: 两个订单都不存在，下新订单
    if not buy_exists and not sell_exists:
        print(f"{BeijingTime()} | [{sym}] 两个订单都不存在，下新订单...")
        
        # 下买单
        buy_qty = align_decimal_places(size_precision, base_amount / buy_price)
        # 使用place_order直接下单，指定价格
        buy_oid, buy_err = engine.cex_driver.place_order(
            symbol=sym, 
            side="buy", 
            order_type="limit", 
            size=buy_qty, 
            price=buy_price
        )
        if buy_err:
            print(f"[{sym}] 买单失败: {buy_err}")
        else:
            data["buy_order_id"] = buy_oid
            print(f"[{sym}] 买单已下: {buy_qty} @ {buy_price}, id={buy_oid}")
        
        # 下卖单
        sell_qty = align_decimal_places(size_precision, base_amount / sell_price)
        # 使用place_order直接下单，指定价格
        sell_oid, sell_err = engine.cex_driver.place_order(
            symbol=sym, 
            side="sell", 
            order_type="limit", 
            size=sell_qty, 
            price=sell_price
        )
        if sell_err:
            print(f"{BeijingTime()} | [{sym}] 卖单失败: {sell_err}")
        else:
            data["sell_order_id"] = sell_oid
            print(f"{BeijingTime()} | [{sym}] 卖单已下: {sell_qty} @ {sell_price}, id={sell_oid}")
        
        return True
    
    # 情况2: 买单成交，卖单还在
    elif not buy_exists and sell_exists:
        print(f"{BeijingTime()} | [{sym}] 买单成交！调整策略...")
        
        # 更新初始价格
        price_now = engine.cex_driver.get_price_now(sym)
        data["baseline_price"] = (baseline_price + price_now) / 2 * config["buy_move_step"] if price_now < baseline_price else baseline_price * config["buy_move_step"]
        new_baseline_price = data["baseline_price"]
        
        # 计算新价格
        new_buy_price = align_decimal_places(price_precision,  new_baseline_price * config["buy_grid_step"])
        new_sell_price = align_decimal_places(price_precision,  new_baseline_price * config["sell_grid_step"])
        
        # 下新买单
        buy_qty = align_decimal_places(size_precision, base_amount / new_buy_price)
        buy_oid, buy_err = engine.cex_driver.place_order(
            symbol=sym, 
            side="buy", 
            order_type="limit", 
            size=buy_qty, 
            price=new_buy_price
        )
        if buy_err:
            print(f"{BeijingTime()} | [{sym}] 新买单失败: {buy_err}")
        else:
            data["buy_order_id"] = buy_oid
            print(f"{BeijingTime()} | [{sym}] 新买单已下: {buy_qty} @ {new_buy_price}, id={buy_oid}")
        
        # 改单现有卖单
        if sell_order_id:
            sell_qty = align_decimal_places(size_precision, base_amount / new_sell_price)
            new_sell_oid, amend_err = engine.cex_driver.amend_order(
                order_id=sell_order_id,
                symbol=sym,
                price=new_sell_price,
                size=sell_qty
            )
            if amend_err:
                print(f"{BeijingTime()} | [{sym}] 改单失败: {amend_err}")
            else:
                data["sell_order_id"] = new_sell_oid
                print(f"{BeijingTime()} | [{sym}] 卖单已改单: {sell_qty} @ {new_sell_price}, 新id={new_sell_oid}")
        
        return True
    
    # 情况3: 卖单成交，买单还在
    elif buy_exists and not sell_exists:
        print(f"{BeijingTime()} | [{sym}] 卖单成交！调整策略...")
        
        # 更新初始价格
        price_now = engine.cex_driver.get_price_now(sym)
        data["baseline_price"] = (baseline_price + price_now) / 2 * config["sell_move_step"] if price_now > baseline_price else baseline_price * config["sell_move_step"]
        new_baseline_price = data["baseline_price"]
        
        # 计算新价格
        new_buy_price = align_decimal_places(price_precision,  new_baseline_price * config["buy_grid_step"])
        new_sell_price = align_decimal_places(price_precision,  new_baseline_price * config["sell_grid_step"])
        
        # 改单现有买单
        if buy_order_id:
            buy_qty = align_decimal_places(size_precision, base_amount / new_buy_price)
            new_buy_oid, amend_err = engine.cex_driver.amend_order(
                order_id=buy_order_id,
                symbol=sym,
                price=new_buy_price,
                size=buy_qty
            )
            if amend_err:
                print(f"{BeijingTime()} | [{sym}] 改单失败: {amend_err}")
            else:
                data["buy_order_id"] = new_buy_oid
                print(f"{BeijingTime()} | [{sym}] 买单已改单: {buy_qty} @ {new_buy_price}, 新id={new_buy_oid}")
        
        # 下新卖单
        sell_qty = align_decimal_places(size_precision, base_amount / new_sell_price)
        sell_oid, sell_err = engine.cex_driver.place_order(
            symbol=sym, 
            side="sell", 
            order_type="limit", 
            size=sell_qty, 
            price=new_sell_price
        )
        if sell_err:
            print(f"{BeijingTime()} | [{sym}] 新卖单失败: {sell_err}")
        else:
            data["sell_order_id"] = sell_oid
            print(f"{BeijingTime()} | [{sym}] 新卖单已下: {sell_qty} @ {new_sell_price}, id={sell_oid}")
        
        return True
    
    # 情况4: 两个订单都在，无事发生
    else:
        return False

def print_position(account, sym, pos, baseline_price, start_ts):
    """
    打印实时仓位信息 + 起步价
    :param sym: 交易对
    :param pos: driver.get_position 返回的单个仓位(dict)
    :param baseline_price: 手动设定的起步价
    :param start_ts: 启动时间戳
    """
    uptime = int(time.time() - start_ts)
    hh = uptime // 3600
    mm = (uptime % 3600) // 60
    ss = uptime % 60
    if not pos:
        output = f"=== [仓位监控] | Account {account} | 当前没有仓位： {sym} | Uptime {hh:02d}:{mm:02d}:{ss:02d} ==="
    else:
        # 从仓位数据里拿需要的字段
        price_now = float(pos.get("markPrice", 0) or 0)
        avg_cost = float(pos.get("entryPrice", 0) or 0)
        size = float(pos.get("quantity", 0) or 0)
        side = pos.get("side", "?")
        pnlUnrealized = float(pos.get("pnlUnrealized", 0) or 0)

        change_pct = (price_now - baseline_price) / baseline_price * 100 if baseline_price else 0.0

        header = f"[仓位监控] {sym} | Account {account} | Uptime {hh:02d}:{mm:02d}:{ss:02d}"
        line = (
            f"现价={round_dynamic(price_now)} | "
            f"起步价={round_dynamic(baseline_price)} | "
            f"数量={round_to_two_digits(size)} | "
            f"方向={side} | "
            f"涨跌幅={change_pct:+.2f}%"
        )
        output = header + line 
    if len(output) < 110:
        output += ' ' * (110 - len(output))
    print('\r' + output, end='')

def load_config():
    """
    加载配置文件
    支持多交易所多账户配置
    配置文件格式: grid_config_{exchange}_{account}.json
    """
    configs = []
    
    # 默认配置
    default_config = {
        "exchange": "bp",
        "account": 0,
        "base_amount": 8.88,
        "force_refresh": False,
        "buy_grid_step": 0.966,
        "sell_grid_step": 1.018,
        "buy_move_step": 0.99,
        "sell_move_step": 1.01,
        "MODE": "DEACTIVATED",
        "description": "网格策略配置 - 请根据实际情况修改参数"
    }
    
    # 尝试加载多个配置文件
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(current_dir, "configs")
    
    # 创建配置文件夹（如果不存在）
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
        print(f"✓ 创建配置文件夹: {config_dir}")
    
    # 支持的交易所和账户组合
    exchange_accounts = [
        ("bp", 0), ("bp", 1), ("bp", 3), ("bp", 4), ("bp", 5), ("bp", 6),
        ("okx", 0), ("okx", 1), ("okx", 2), ("okx", 3), ("okx", 4), ("okx", 5), ("okx", 6),
        ("bnb", 0), ("bnb", 1), ("bnb", 2), ("bnb", 3), ("bnb", 4), ("bnb", 5), ("bnb", 6)
    ]
    
    for exchange, account in exchange_accounts:
        config_file = os.path.join(config_dir, f"grid_config_{exchange}_{account}.json")
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                if config["MODE"] == 'DEACTIVATED':
                    continue
                # 验证必要字段
                required_fields = ["exchange", "account", "base_amount", "buy_grid_step", "sell_grid_step", "buy_move_step", "sell_move_step"]
                if all(field in config for field in required_fields):
                    configs.append(config)
                    print(f"✓ 加载配置: {exchange}-{account}")
                else:
                    print(f"⚠ 配置文件缺少必要字段: {config_file}")
                    
            except Exception as e:
                print(f"✗ 加载配置文件失败 {config_file}: {e}")
        else:
            # 创建默认配置文件
            config = default_config.copy()
            config["exchange"] = exchange
            config["account"] = account
            config["MODE"] = 'DEACTIVATED'
            
            try:
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                print(f"✓ 创建默认配置文件: {config_file}")
            except Exception as e:
                print(f"✗ 创建配置文件失败 {config_file}: {e}")
    
    # 如果没有找到任何配置文件，使用默认配置
    if not configs:
        print("⚠ 未找到配置文件，使用默认配置")
        configs = []
    # 检查是否为首次运行（通过标记文件）
    first_run_flag = os.path.join(config_dir, ".first_run_flag")
    # 检查标记文件是否存在，且路径是否与当前脚本一致
    need_confirm = True
    if os.path.exists(first_run_flag):
        try:
            with open(first_run_flag, "r") as f:
                flag_content = f.read().strip()
            # 获取当前脚本绝对路径
            current_file_path = os.path.abspath(__file__)
            # 标记文件内容为首次运行时写入的脚本路径
            if flag_content == current_file_path:
                need_confirm = False
        except Exception as e:
            print(f"读取首次运行标记文件异常: {e}")
    if need_confirm:
        print("\n=== 检测到首次运行！请确认以下配置文件是否需要启用 ===\n")
        confirmed_configs = []
        for config in configs:
            print(f"\n------------------------------")
            print(f"配置文件: grid_config_{config['exchange']}_{config['account']}.json")
            print(json.dumps(config, ensure_ascii=False, indent=2))
            resp = input("是否启用该配置？(y/n, 默认y): ").strip().lower()
            if resp in ["", "y", "yes", "是"]:
                confirmed_configs.append(config)
                print("✓ 已保留该配置。")
            else:
                print("✗ 已丢弃该配置。")
        configs = confirmed_configs
        # 创建标记文件，表示已完成首次确认
        with open(first_run_flag, "w") as f:
            f.write(os.path.abspath(__file__))
        print("\n首次配置确认已完成，后续将不再提示。")
    return configs

def show_help():
    """显示帮助信息"""
    print("""
=== 网格策略使用说明 (配置文件版) ===

用法: python Grid_with_more_gap.py

配置文件:
  策略使用配置文件进行参数设置，配置文件位于 configs/ 文件夹下:
  configs/grid_config_{exchange}_{account}.json
  
  示例配置文件:
  - configs/grid_config_bp_0.json    # Backpack账户0
  - configs/grid_config_bp_3.json    # Backpack账户3  
  - configs/grid_config_okx_0.json   # OKX账户0

配置文件格式:
{
  "exchange": "bp",           # 交易所名称 (bp/okx)
  "account": 0,               # 账户ID (0-4)
  "base_amount": 8.88,        # 基础交易金额 (USDT)
  "force_refresh": false,     # 是否强制刷新缓存
  "description": "配置说明"    # 配置描述
}

策略特性:
  ✓ 订单管理策略 (基于get_open_orders)
  ✓ 自动网格下单 (买单@0.966x, 卖单@1.018x)
  ✓ 成交后自动调整 (买单成交→0.99x, 卖单成交→1.01x)
  ✓ 智能改单机制 (存在订单直接改单，不存在则下新单)
  ✓ 订单状态监控 (实时检查订单存在性)
  ✓ 本地持仓缓存 (6小时内自动加载)
  ✓ 完整操作日志记录
  ✓ 多账户配置文件支持

策略逻辑:
  1. 自动加载所有配置文件
  2. 获取全局所有订单
  3. 检查每个币种的买单和卖单是否存在
  4. 如果都不存在 → 下新订单
  5. 如果买单成交 → 下新买单 + 改单现有卖单
  6. 如果卖单成交 → 改单现有买单 + 下新卖单
  7. 如果都在 → 等待下一轮

配置文件优势:
  ✓ 支持多交易所多账户
  ✓ 参数持久化保存
  ✓ 自动创建默认配置
  ✓ 独立配置管理
""")

def grid_with_more_gap(engines=None, exchs=None, force_refresh=None, base_amount=None, configs=None):
    print(f"使用交易所: {exchs}")
    if force_refresh is None:
        force_refresh = [False] * len(engines)
    for fr, engine, exch in zip(force_refresh, engines, exchs):
        if fr:
            print(f"🔄 强制刷新模式：忽略本地缓存 {exch}-{engine.account}")
    if base_amount is None:
        base_amount = [8.88] * len(engines)
    # 记录策略启动
    for engine, exch, fr, ba in zip(engines, exchs, force_refresh, base_amount):
        engine.monitor.record_operation("StrategyStart", "Grid-Order-Management", {
            "exchange": exch,
            "strategy": "Grid-Order-Management",
            "version": "3.0",
            "force_refresh": fr,
            "base_amount": ba
        })

    # 获取持仓（支持缓存）
    GridPositions_all = [get_all_GridPositions(engine, exch, use_cache=True if not fr else False) for engine, exch, fr in zip(engines, exchs, force_refresh)]
    for engine, GridPositions in zip(engines, GridPositions_all):
        if not GridPositions:
            print("没有持仓，退出。")
            engine.monitor.record_operation("StrategyExit", "Grid-Order-Management", {
                "reason": "No GridPositions found"
            })
            return
        print("初始持仓:", GridPositions)

    # 创建关注币种文件夹
    current_dir = os.path.dirname(os.path.abspath(__file__))
    symbols_dir = os.path.join(current_dir, "symbols")
    
    if not os.path.exists(symbols_dir):
        os.makedirs(symbols_dir)
        print(f"✓ 创建关注币种文件夹: {symbols_dir}")

    # 为每个交易所和账户组合处理关注币种
    focus_symbols_all = {}
    
    for engine, exch, GridPositions in zip(engines, exchs, GridPositions_all):
        symbols_file = f"{exch}_Account{engine.account}_focus_symbols.json"
        symbols_file_path = os.path.join(symbols_dir, symbols_file)
        
        # 读取关注币种集合
        if os.path.exists(symbols_file_path):
            try:
                with open(symbols_file_path, "r", encoding="utf-8") as f:
                    focus_symbols = set(json.load(f))
                print(f"✓ 加载关注币种: {exch}-{engine.account}")
            except Exception as e:
                print(f"✗ 读取关注币种文件失败 {symbols_file_path}: {e}")
                focus_symbols = set()
        else:
            # 文件不存在，使用当前GridPositions的币种
            focus_symbols = set(GridPositions.keys())
            # 保存币种集合到文件
            try:
                with open(symbols_file_path, "w", encoding="utf-8") as f:
                    json.dump(list(focus_symbols), f, ensure_ascii=False, indent=2)
                print(f"✓ 创建关注币种文件: {symbols_file_path}")
            except Exception as e:
                print(f"✗ 保存关注币种文件失败 {symbols_file_path}: {e}")
        
        focus_symbols_all[f"{exch}_{engine.account}"] = focus_symbols
    
    # 合并所有关注币种（用于后续处理）
    all_focus_symbols = set()
    for symbols in focus_symbols_all.values():
        all_focus_symbols.update(symbols)

    # 对齐GridPositions到关注币种集合
    for engine, exch, GridPositions in zip(engines, exchs, GridPositions_all):
        key = f"{exch}_{engine.account}"
        focus_symbols = focus_symbols_all.get(key, set())
        
        # 1. 如果少了币种，则币种置空仓位
        for sym in focus_symbols:
            if sym not in GridPositions:
                # 置空仓位
                price_now = engine.cex_driver.get_price_now(sym)
                GridPositions[sym] =  {
                        "baseline_price": price_now,
                        "avg_cost": price_now,
                        "size": 0,
                        "side": 0,
                        'pnlUnrealized': 0,
                        "buy_order_id": None,  # 买单订单ID
                        "sell_order_id": None,  # 卖单订单ID
                    }
        # 2. 如果多了币种，则撤销该仓位的订单并移除
        remove_syms = []
        for sym in list(GridPositions.keys()):
            if sym not in focus_symbols:
                # 撤销该币种的订单
                buy_order_id = GridPositions[sym].get("buy_order_id")
                sell_order_id = GridPositions[sym].get("sell_order_id")
                for oid in [buy_order_id, sell_order_id]:
                    if oid:
                        try:
                            cancel_result, cancel_err = engine.cex_driver.revoke_order(order_id=oid, symbol=sym)
                            if cancel_err:
                                print(f"[{sym}] 撤销订单 {oid} 失败: {cancel_err}")
                            else:
                                print(f"[{sym}] 已撤销订单 {oid}")
                        except Exception as e:
                            print(f"[{sym}] 撤销订单 {oid} 异常: {e}")
                remove_syms.append(sym)
        for sym in remove_syms:
            del GridPositions[sym]

    start_ts = time.time()
    sleep_time = 1.88
    need_to_update = False
    while True:
        try:
            for engine, GridPositions, ba, config in zip(engines, GridPositions_all, base_amount, configs):
            # 获取全局所有订单
                open_orders, err = engine.cex_driver.get_open_orders(symbol=None, onlyOrderId=True, keep_origin=False)
                if err:
                    print(f"获取订单失败: {err}")
                    time.sleep(sleep_time)
                    continue
                
                if not isinstance(open_orders, list) or not open_orders:
                    open_orders = []
                origin_pos, err = engine.cex_driver.get_position(symbol=None, keep_origin=False)
                poses = {}
                for pos in origin_pos:
                    poses[pos["symbol"]] = pos
                if err or not poses:
                    continue
                for sym, data in GridPositions.items():
                    try:
                        time.sleep(sleep_time)
                        # 获取当前持仓信息用于显示
                        if sym not in poses:
                            pos = {}
                        else:
                            pos = poses[sym]
                        if abs(float(pos["quantityUSD"])) < 10 and abs(float(pos["quantityUSD"])) > 0:
                            time.sleep(sleep_time)
                            continue
                        exchange_limits_info, err = engine.cex_driver.exchange_limits(symbol=sym)
                        if err:
                            print('CEX DRIVER.exchange_limits error ', err)
                            return None, err
                        price_precision = exchange_limits_info['price_precision']
                        min_order_size = exchange_limits_info['min_order_size']
                        baseline_price = data["baseline_price"]
                        print_position(engine.account, sym, pos, baseline_price, start_ts)
                        
                        # 使用新的订单管理逻辑
                        order_updated = manage_grid_orders(engine, sym, data, open_orders, price_precision, min_order_size, 6.66 if engine.account==-1 else ba, config)
                        
                        # 如果有订单更新，保存数据
                        if order_updated:
                            need_to_update = True

                    except Exception as e:
                        print(f"[{sym}] 循环异常:", e)
                        break
                if need_to_update:
                    save_GridPositions(GridPositions, exch, engine.account)
                    need_to_update = False
                # 定期保存数据
                if time.time() - start_ts % 1800 < sleep_time * len(GridPositions):
                    save_GridPositions(GridPositions, exch, engine.account)
        except KeyboardInterrupt:
            print("手动退出。")
            engine.monitor.record_operation("StrategyExit", "Grid-Order-Management", {
                "reason": "Manual interrupt",
                "uptime": time.time() - start_ts
            })
            sys.exit()

if __name__ == '__main__':
    print("\n=== 网格策略 (配置文件版) ===")

    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:
        show_help()
        sys.exit()
    
    # 加载配置文件
    configs = load_config()
    
    if not configs:
        print("❌ 未找到有效配置文件，退出")
        sys.exit(1)
    
    # 自动用当前文件名（去除后缀）作为默认策略名，细节默认为COMMON
    default_strategy = os.path.splitext(os.path.basename(__file__))[0].upper()
    
    # 根据配置文件初始化交易所和引擎
    engines = []
    exchs = []
    force_refresh = []
    base_amount = []
    
    for config in configs:
        try:
            exchange, account = config["exchange"], config["account"]
            exch, engine = pick_exchange(exchange, account, strategy=default_strategy, strategy_detail="COMMON")
            engines.append(engine)
            exchs.append(exch)
            force_refresh.append(config.get("force_refresh", False))
            base_amount.append(config.get("base_amount", 8.88))
            print(f"✓ 初始化 {exchange}-{account} 成功")
        except Exception as e:
            print(f"✗ 初始化 {config['exchange']}-{config['account']} 失败: {e}")
    
    if not engines:
        print("❌ 没有成功初始化任何交易所，退出")
        sys.exit(1)
    
    print(f"🚀 启动网格策略，共 {len(engines)} 个账户")
    grid_with_more_gap(engines, exchs, force_refresh, base_amount, configs)