# CTOS 套利策略设计文档

## 概述

本文档设计 CTOS 系统的套利策略框架，包括跨交易所套利和预测市场 delta 中性套利策略。设计遵循 CTOS 的"操作系统式"架构理念，提供统一、可扩展、高可靠的套利执行环境。

---

## 1. 跨交易所套利策略设计

### 1.1 策略架构

```
apps/strategies/arbitrage/
├── cross_exchange/           # 跨交易所套利
│   ├── __init__.py
│   ├── base_arbitrage.py     # 套利策略基类
│   ├── price_monitor.py      # 价格监控引擎
│   ├── execution_engine.py   # 套利执行引擎
│   ├── risk_manager.py       # 套利风控模块
│   ├── strategies/
│   │   ├── spot_arbitrage.py      # 现货套利
│   │   ├── futures_arbitrage.py   # 期货套利
│   │   ├── funding_rate_arb.py    # 资金费率套利
│   │   └── triangular_arb.py      # 三角套利
│   └── configs/
│       ├── arbitrage_config.yaml  # 套利配置
│       └── exchange_pairs.yaml    # 交易所配对配置
```

### 1.2 核心组件设计

#### 1.2.1 价格监控引擎 (PriceMonitor)

```python
class PriceMonitor:
    """跨交易所价格监控引擎"""
    
    def __init__(self, exchanges: List[str], symbols: List[str]):
        self.exchanges = exchanges
        self.symbols = symbols
        self.price_feeds = {}  # {exchange: {symbol: price_data}}
        self.arbitrage_opportunities = []
        
    async def start_monitoring(self):
        """启动多交易所价格监控"""
        tasks = []
        for exchange in self.exchanges:
            task = asyncio.create_task(self._monitor_exchange(exchange))
            tasks.append(task)
        await asyncio.gather(*tasks)
    
    async def _monitor_exchange(self, exchange: str):
        """监控单个交易所价格"""
        driver = self._get_driver(exchange)
        for symbol in self.symbols:
            # 订阅实时价格
            await driver.subscribe_ticks(symbol, self._on_price_update)
    
    def _on_price_update(self, exchange: str, symbol: str, price_data: dict):
        """价格更新回调"""
        self.price_feeds[exchange][symbol] = price_data
        self._detect_arbitrage_opportunities(symbol)
    
    def _detect_arbitrage_opportunities(self, symbol: str):
        """检测套利机会"""
        prices = {}
        for exchange in self.exchanges:
            if symbol in self.price_feeds[exchange]:
                prices[exchange] = self.price_feeds[exchange][symbol]['price']
        
        if len(prices) >= 2:
            # 计算价差
            max_price = max(prices.values())
            min_price = min(prices.values())
            spread = (max_price - min_price) / min_price
            
            if spread > self.min_spread_threshold:
                opportunity = {
                    'symbol': symbol,
                    'buy_exchange': min(prices, key=prices.get),
                    'sell_exchange': max(prices, key=prices.get),
                    'buy_price': min_price,
                    'sell_price': max_price,
                    'spread': spread,
                    'timestamp': time.time()
                }
                self.arbitrage_opportunities.append(opportunity)
```

#### 1.2.2 套利执行引擎 (ArbitrageExecutor)

```python
class ArbitrageExecutor:
    """套利执行引擎"""
    
    def __init__(self, risk_manager: ArbitrageRiskManager):
        self.risk_manager = risk_manager
        self.active_arbitrages = {}  # {arb_id: arbitrage_state}
        
    async def execute_arbitrage(self, opportunity: dict) -> bool:
        """执行套利机会"""
        arb_id = f"{opportunity['symbol']}_{int(time.time())}"
        
        try:
            # 1. 风险检查
            if not self.risk_manager.validate_opportunity(opportunity):
                return False
            
            # 2. 计算最优交易量
            quantity = self._calculate_optimal_quantity(opportunity)
            
            # 3. 同步下单（关键：确保原子性）
            buy_order, sell_order = await self._place_simultaneous_orders(
                opportunity, quantity
            )
            
            # 4. 监控执行状态
            await self._monitor_execution(arb_id, buy_order, sell_order)
            
            return True
            
        except Exception as e:
            logger.error(f"套利执行失败 {arb_id}: {e}")
            await self._cleanup_failed_arbitrage(arb_id)
            return False
    
    async def _place_simultaneous_orders(self, opportunity: dict, quantity: float):
        """同步下单"""
        buy_driver = self._get_driver(opportunity['buy_exchange'])
        sell_driver = self._get_driver(opportunity['sell_exchange'])
        
        # 使用 asyncio.gather 确保同时下单
        buy_task = asyncio.create_task(
            buy_driver.place_order(
                symbol=opportunity['symbol'],
                side='buy',
                order_type='market',
                size=quantity
            )
        )
        sell_task = asyncio.create_task(
            sell_driver.place_order(
                symbol=opportunity['symbol'],
                side='sell',
                order_type='market',
                size=quantity
            )
        )
        
        buy_order, sell_order = await asyncio.gather(buy_task, sell_task)
        return buy_order, sell_order
```

### 1.3 套利策略实现

#### 1.3.1 现货套利策略

```python
class SpotArbitrageStrategy(BaseArbitrageStrategy):
    """现货套利策略"""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.min_spread = config.get('min_spread', 0.002)  # 最小价差 0.2%
        self.max_position_size = config.get('max_position_size', 1000)  # 最大仓位
        self.transfer_enabled = config.get('transfer_enabled', True)  # 是否支持转账
        
    async def detect_opportunity(self, symbol: str) -> Optional[dict]:
        """检测现货套利机会"""
        prices = await self._get_spot_prices(symbol)
        
        if len(prices) < 2:
            return None
            
        # 计算价差
        buy_exchange = min(prices, key=prices.get)
        sell_exchange = max(prices, key=prices.get)
        
        spread = (prices[sell_exchange] - prices[buy_exchange]) / prices[buy_exchange]
        
        if spread > self.min_spread:
            return {
                'type': 'spot_arbitrage',
                'symbol': symbol,
                'buy_exchange': buy_exchange,
                'sell_exchange': sell_exchange,
                'buy_price': prices[buy_exchange],
                'sell_price': prices[sell_exchange],
                'spread': spread,
                'estimated_profit': self._calculate_profit(prices, spread)
            }
        
        return None
    
    def _calculate_profit(self, prices: dict, spread: float) -> float:
        """计算预期利润（扣除手续费和转账成本）"""
        base_profit = spread * self.max_position_size
        fees = self._calculate_total_fees()
        transfer_cost = self._calculate_transfer_cost() if self.transfer_enabled else 0
        
        return base_profit - fees - transfer_cost
```

#### 1.3.2 资金费率套利策略

```python
class FundingRateArbitrageStrategy(BaseArbitrageStrategy):
    """资金费率套利策略"""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.min_funding_rate = config.get('min_funding_rate', 0.0001)  # 最小资金费率
        self.hedge_ratio = config.get('hedge_ratio', 1.0)  # 对冲比例
        
    async def detect_opportunity(self, symbol: str) -> Optional[dict]:
        """检测资金费率套利机会"""
        funding_rates = await self._get_funding_rates(symbol)
        spot_prices = await self._get_spot_prices(symbol)
        
        # 寻找资金费率差异
        max_rate_exchange = max(funding_rates, key=funding_rates.get)
        min_rate_exchange = min(funding_rates, key=funding_rates.get)
        
        rate_spread = funding_rates[max_rate_exchange] - funding_rates[min_rate_exchange]
        
        if rate_spread > self.min_funding_rate:
            return {
                'type': 'funding_rate_arbitrage',
                'symbol': symbol,
                'long_exchange': min_rate_exchange,  # 做多（支付较低费率）
                'short_exchange': max_rate_exchange,  # 做空（收取较高费率）
                'rate_spread': rate_spread,
                'spot_prices': spot_prices,
                'estimated_profit': self._calculate_funding_profit(rate_spread)
            }
        
        return None
```

---

## 2. 预测市场 Delta 中性套利策略设计

### 2.1 策略架构

```
apps/strategies/arbitrage/
├── prediction_market/        # 预测市场套利
│   ├── __init__.py
│   ├── market_data_integration.py  # 市场数据整合
│   ├── delta_neutral_engine.py     # Delta 中性引擎
│   ├── prediction_models.py        # 预测模型
│   ├── hedging_strategies.py       # 对冲策略
│   └── strategies/
│       ├── options_arbitrage.py    # 期权套利
│       ├── futures_arbitrage.py    # 期货套利
│       └── cross_asset_arb.py      # 跨资产套利
```

### 2.2 市场数据整合模块

```python
class MarketDataIntegration:
    """预测市场数据整合模块"""
    
    def __init__(self, data_sources: List[str]):
        self.data_sources = data_sources
        self.market_data = {}
        self.correlation_matrix = {}
        
    async def start_data_collection(self):
        """启动多源数据收集"""
        tasks = []
        for source in self.data_sources:
            if source == 'crypto_exchanges':
                task = asyncio.create_task(self._collect_crypto_data())
            elif source == 'traditional_markets':
                task = asyncio.create_task(self._collect_traditional_data())
            elif source == 'prediction_markets':
                task = asyncio.create_task(self._collect_prediction_data())
            tasks.append(task)
        
        await asyncio.gather(*tasks)
    
    async def _collect_crypto_data(self):
        """收集加密货币市场数据"""
        # 从 OKX, Binance, Backpack 收集价格、波动率、资金费率等
        pass
    
    async def _collect_traditional_data(self):
        """收集传统金融市场数据"""
        # 从 Bloomberg, Yahoo Finance 等收集股票、债券、商品数据
        pass
    
    async def _collect_prediction_data(self):
        """收集预测市场数据"""
        # 从 Polymarket, PredictIt 等收集预测市场数据
        pass
    
    def calculate_correlations(self, timeframe: str = '1h'):
        """计算资产间相关性"""
        # 实现动态相关性计算
        pass
```

### 2.3 Delta 中性引擎

```python
class DeltaNeutralEngine:
    """Delta 中性套利引擎"""
    
    def __init__(self, config: dict):
        self.config = config
        self.positions = {}  # {asset: position_info}
        self.delta_target = 0.0  # 目标 Delta 值
        self.max_delta_deviation = config.get('max_delta_deviation', 0.1)
        
    async def maintain_delta_neutrality(self, market_data: dict):
        """维持 Delta 中性"""
        current_delta = self._calculate_portfolio_delta()
        delta_deviation = abs(current_delta - self.delta_target)
        
        if delta_deviation > self.max_delta_deviation:
            await self._rebalance_positions(current_delta, market_data)
    
    def _calculate_portfolio_delta(self) -> float:
        """计算投资组合总 Delta"""
        total_delta = 0.0
        for asset, position in self.positions.items():
            total_delta += position['quantity'] * position['delta']
        return total_delta
    
    async def _rebalance_positions(self, current_delta: float, market_data: dict):
        """重新平衡仓位以维持 Delta 中性"""
        delta_to_hedge = -current_delta
        
        # 选择最优对冲工具
        hedge_instrument = self._select_hedge_instrument(delta_to_hedge, market_data)
        
        if hedge_instrument:
            await self._execute_hedge_trade(hedge_instrument, delta_to_hedge)
    
    def _select_hedge_instrument(self, delta_to_hedge: float, market_data: dict):
        """选择最优对冲工具"""
        # 基于成本、流动性、相关性选择对冲工具
        candidates = []
        
        # 期货对冲
        for future in market_data.get('futures', []):
            cost = self._calculate_hedge_cost(future, delta_to_hedge)
            candidates.append({
                'type': 'future',
                'instrument': future,
                'cost': cost,
                'liquidity': future.get('liquidity', 0)
            })
        
        # 期权对冲
        for option in market_data.get('options', []):
            cost = self._calculate_hedge_cost(option, delta_to_hedge)
            candidates.append({
                'type': 'option',
                'instrument': option,
                'cost': cost,
                'liquidity': option.get('liquidity', 0)
            })
        
        # 选择成本最低且流动性充足的工具
        return min(candidates, key=lambda x: x['cost'] + (1/x['liquidity'] if x['liquidity'] > 0 else float('inf')))
```

### 2.4 预测模型集成

```python
class PredictionModelIntegration:
    """预测模型集成模块"""
    
    def __init__(self, models: List[str]):
        self.models = models
        self.model_weights = {}
        self.ensemble_predictions = {}
        
    async def generate_predictions(self, market_data: dict) -> dict:
        """生成集成预测"""
        predictions = {}
        
        for model_name in self.models:
            if model_name == 'lstm_price_prediction':
                pred = await self._lstm_predict(market_data)
            elif model_name == 'sentiment_analysis':
                pred = await self._sentiment_predict(market_data)
            elif model_name == 'technical_indicators':
                pred = await self._technical_predict(market_data)
            elif model_name == 'fundamental_analysis':
                pred = await self._fundamental_predict(market_data)
            
            predictions[model_name] = pred
        
        # 集成预测
        ensemble_pred = self._ensemble_predictions(predictions)
        return ensemble_pred
    
    def _ensemble_predictions(self, predictions: dict) -> dict:
        """集成多个模型的预测结果"""
        # 实现加权平均、投票等集成方法
        pass
```

---

## 3. 统一套利策略框架

### 3.1 基类设计

```python
class BaseArbitrageStrategy:
    """套利策略基类"""
    
    def __init__(self, config: dict):
        self.config = config
        self.strategy_id = config.get('strategy_id', f"arb_{int(time.time())}")
        self.status = 'stopped'
        self.risk_manager = ArbitrageRiskManager(config.get('risk', {}))
        self.performance_tracker = PerformanceTracker(self.strategy_id)
        
    async def start(self):
        """启动策略"""
        self.status = 'running'
        await self._initialize()
        await self._main_loop()
    
    async def stop(self):
        """停止策略"""
        self.status = 'stopping'
        await self._cleanup_positions()
        self.status = 'stopped'
    
    async def _main_loop(self):
        """主循环"""
        while self.status == 'running':
            try:
                # 检测套利机会
                opportunities = await self.detect_opportunities()
                
                for opportunity in opportunities:
                    if self.risk_manager.validate_opportunity(opportunity):
                        await self.execute_opportunity(opportunity)
                
                await asyncio.sleep(self.config.get('check_interval', 1.0))
                
            except Exception as e:
                logger.error(f"策略主循环异常: {e}")
                await asyncio.sleep(5.0)
    
    async def detect_opportunities(self) -> List[dict]:
        """检测套利机会（子类实现）"""
        raise NotImplementedError
    
    async def execute_opportunity(self, opportunity: dict) -> bool:
        """执行套利机会（子类实现）"""
        raise NotImplementedError
```

### 3.2 风险控制模块

```python
class ArbitrageRiskManager:
    """套利风险控制模块"""
    
    def __init__(self, config: dict):
        self.config = config
        self.max_position_size = config.get('max_position_size', 10000)
        self.max_daily_loss = config.get('max_daily_loss', 1000)
        self.max_concurrent_arbitrages = config.get('max_concurrent_arbitrages', 5)
        self.min_profit_threshold = config.get('min_profit_threshold', 10)
        
    def validate_opportunity(self, opportunity: dict) -> bool:
        """验证套利机会是否满足风险要求"""
        # 1. 检查最大仓位限制
        if not self._check_position_limits(opportunity):
            return False
        
        # 2. 检查日损失限制
        if not self._check_daily_loss_limits():
            return False
        
        # 3. 检查并发套利数量
        if not self._check_concurrent_limits():
            return False
        
        # 4. 检查最小利润阈值
        if not self._check_profit_threshold(opportunity):
            return False
        
        return True
    
    def _check_position_limits(self, opportunity: dict) -> bool:
        """检查仓位限制"""
        required_capital = opportunity.get('required_capital', 0)
        return required_capital <= self.max_position_size
    
    def _check_daily_loss_limits(self) -> bool:
        """检查日损失限制"""
        today_loss = self._get_today_loss()
        return today_loss < self.max_daily_loss
    
    def _check_concurrent_limits(self) -> bool:
        """检查并发套利限制"""
        active_count = self._get_active_arbitrage_count()
        return active_count < self.max_concurrent_arbitrages
    
    def _check_profit_threshold(self, opportunity: dict) -> bool:
        """检查利润阈值"""
        estimated_profit = opportunity.get('estimated_profit', 0)
        return estimated_profit >= self.min_profit_threshold
```

---

## 4. 监控与报告系统

### 4.1 实时监控

```python
class ArbitrageMonitor:
    """套利监控系统"""
    
    def __init__(self):
        self.metrics = {
            'total_opportunities': 0,
            'executed_arbitrages': 0,
            'successful_arbitrages': 0,
            'total_profit': 0.0,
            'total_loss': 0.0,
            'active_positions': 0
        }
        self.alerts = []
    
    def update_metrics(self, event: dict):
        """更新监控指标"""
        event_type = event.get('type')
        
        if event_type == 'opportunity_detected':
            self.metrics['total_opportunities'] += 1
        elif event_type == 'arbitrage_executed':
            self.metrics['executed_arbitrages'] += 1
        elif event_type == 'arbitrage_completed':
            self.metrics['successful_arbitrages'] += 1
            profit = event.get('profit', 0)
            if profit > 0:
                self.metrics['total_profit'] += profit
            else:
                self.metrics['total_loss'] += abs(profit)
    
    def check_alerts(self):
        """检查告警条件"""
        # 检查异常情况并生成告警
        if self.metrics['total_loss'] > self.config.get('max_loss_alert', 5000):
            self.alerts.append({
                'type': 'high_loss',
                'message': f"总损失超过阈值: {self.metrics['total_loss']}",
                'timestamp': time.time()
            })
```

### 4.2 绩效分析

```python
class ArbitragePerformanceAnalyzer:
    """套利绩效分析器"""
    
    def __init__(self, strategy_id: str):
        self.strategy_id = strategy_id
        self.trades = []
        self.performance_metrics = {}
    
    def add_trade(self, trade: dict):
        """添加交易记录"""
        self.trades.append(trade)
        self._update_metrics()
    
    def _update_metrics(self):
        """更新绩效指标"""
        if not self.trades:
            return
        
        # 计算基本指标
        total_trades = len(self.trades)
        profitable_trades = len([t for t in self.trades if t['profit'] > 0])
        win_rate = profitable_trades / total_trades if total_trades > 0 else 0
        
        total_profit = sum(t['profit'] for t in self.trades)
        avg_profit = total_profit / total_trades if total_trades > 0 else 0
        
        # 计算夏普比率
        returns = [t['profit'] for t in self.trades]
        sharpe_ratio = self._calculate_sharpe_ratio(returns)
        
        self.performance_metrics = {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'avg_profit': avg_profit,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': self._calculate_max_drawdown(returns)
        }
    
    def generate_report(self) -> dict:
        """生成绩效报告"""
        return {
            'strategy_id': self.strategy_id,
            'period': self._get_analysis_period(),
            'metrics': self.performance_metrics,
            'trades_summary': self._get_trades_summary(),
            'recommendations': self._generate_recommendations()
        }
```

---

## 5. 配置管理

### 5.1 套利策略配置

```yaml
# configs/arbitrage_config.yaml
arbitrage:
  global:
    max_concurrent_strategies: 3
    risk_tolerance: "medium"
    monitoring_enabled: true
    
  cross_exchange:
    enabled: true
    exchanges: ["okx", "binance", "backpack"]
    symbols: ["BTC-USDT", "ETH-USDT", "SOL-USDT"]
    min_spread: 0.002
    max_position_size: 10000
    execution_timeout: 30
    
  prediction_market:
    enabled: true
    data_sources: ["crypto_exchanges", "traditional_markets", "prediction_markets"]
    models: ["lstm_price_prediction", "sentiment_analysis", "technical_indicators"]
    delta_target: 0.0
    max_delta_deviation: 0.1
    rebalance_interval: 300
    
  risk_management:
    max_daily_loss: 5000
    max_position_size: 20000
    stop_loss_threshold: 0.05
    emergency_stop_enabled: true
```

### 5.2 交易所配对配置

```yaml
# configs/exchange_pairs.yaml
exchange_pairs:
  okx_binance:
    exchanges: ["okx", "binance"]
    supported_symbols: ["BTC-USDT", "ETH-USDT", "SOL-USDT"]
    transfer_enabled: true
    transfer_fee: 0.001
    min_transfer_amount: 100
    
  okx_backpack:
    exchanges: ["okx", "backpack"]
    supported_symbols: ["SOL-USDT", "BTC-USDT"]
    transfer_enabled: false
    arbitrage_type: "price_only"
```

---

## 6. 实施路线图

### 阶段 1: 基础框架 (2-3 周)
- [ ] 实现 BaseArbitrageStrategy 基类
- [ ] 实现 ArbitrageRiskManager 风险控制
- [ ] 实现基础监控和报告系统
- [ ] 完成配置管理模块

### 阶段 2: 跨交易所套利 (3-4 周)
- [ ] 实现 PriceMonitor 价格监控引擎
- [ ] 实现 ArbitrageExecutor 执行引擎
- [ ] 开发现货套利策略
- [ ] 开发资金费率套利策略
- [ ] 集成测试和优化

### 阶段 3: 预测市场套利 (4-5 周)
- [ ] 实现 MarketDataIntegration 数据整合
- [ ] 实现 DeltaNeutralEngine Delta 中性引擎
- [ ] 集成预测模型
- [ ] 开发期权和期货套利策略
- [ ] 实现动态对冲机制

### 阶段 4: 高级功能 (2-3 周)
- [ ] 实现机器学习模型集成
- [ ] 开发高级风险控制算法
- [ ] 实现实时性能优化
- [ ] 完善监控和告警系统

---

## 7. 技术要点

### 7.1 关键挑战
1. **延迟控制**: 套利机会转瞬即逝，需要极低延迟的执行
2. **同步执行**: 确保多交易所订单的原子性
3. **风险控制**: 实时监控和动态调整风险参数
4. **数据质量**: 多源数据的清洗和标准化
5. **模型集成**: 多个预测模型的协调和集成

### 7.2 解决方案
1. **异步架构**: 使用 asyncio 实现高并发
2. **分布式锁**: 使用 Redis 实现分布式同步
3. **实时风控**: 基于事件驱动的风险监控
4. **数据管道**: 使用 Apache Kafka 实现实时数据流
5. **模型服务**: 使用微服务架构部署预测模型

---

## 8. 总结

本设计为 CTOS 提供了完整的套利策略框架，支持跨交易所套利和预测市场 delta 中性套利。设计遵循 CTOS 的"操作系统式"理念，提供统一、可扩展、高可靠的套利执行环境。

通过模块化设计和清晰的接口规范，可以快速开发和部署新的套利策略，同时保证系统的稳定性和可维护性。风险控制模块确保在追求利润的同时有效控制风险，监控和报告系统提供全面的策略表现分析。

