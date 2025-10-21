# 持仓管理重构方案

## 问题诊断

当前架构存在**双重持仓记录**：
1. `PositionManager.holdings` - 策略层维护
2. 交易系统持仓 - `TradeExecutor.get_holdings()` 查询

这导致需要手动同步，容易出现不一致。

## 推荐方案：元数据管理模式

### 核心思想
- **持仓数量/金额** → 只从交易系统查询（单一数据源）
- **策略元数据** → PositionManager 维护（交易系统没有的信息）

### 重构后的职责划分

#### `TradeExecutor`（唯一持仓真相）
```python
def get_holdings(account, C=None):
    """返回: {stock_code: {'volume': xxx, 'cost': xxx, 'available': xxx}}"""
    # 从回测引擎/实盘系统查询，不维护本地状态
```

#### `PositionMetadataManager`（原 PositionManager）
```python
class PositionMetadataManager:
    def __init__(self):
        # 只维护策略相关的元数据
        self.metadata = {}  # {stock_code: {buy_date, score, target_profit, buy_price, ...}}
    
    def add_metadata(self, stock_code, buy_date, score, buy_price, buy_time=None):
        """记录买入元数据（不记录数量）"""
        self.metadata[stock_code] = {
            'buy_date': buy_date,
            'buy_price': buy_price,
            'buy_time': buy_time,
            'score': score,
            'target_profit': self.calc_target_profit(score)
        }
    
    def remove_metadata(self, stock_code):
        """清除元数据"""
        if stock_code in self.metadata:
            del self.metadata[stock_code]
    
    def check_exit_conditions(self, stock_code, current_price, current_date):
        """
        基于元数据判断卖出条件
        注意：不再维护 hold_days，实时计算
        """
        if stock_code not in self.metadata:
            return False, None
        
        meta = self.metadata[stock_code]
        buy_price = meta['buy_price']
        buy_date = meta['buy_date']
        target_profit = meta['target_profit']
        
        # 实时计算持有天数
        hold_days = (current_date - buy_date).days
        pct_change = (current_price - buy_price) / buy_price
        
        if pct_change >= target_profit:
            return True, 'target_profit'
        if pct_change <= STOP_LOSS:
            return True, 'stop_loss'
        if hold_days > MAX_HOLD_DAYS:
            return True, 'max_hold_days'
        
        return False, None
```

### 使用示例

#### 买入流程
```python
# 1. 下单
order_id = trade_executor.buy(account, stock_code, price, volume, ...)

# 2. 仅记录元数据（不记录数量）
strategy.position_metadata_mgr.add_metadata(
    stock_code, buy_date, score, buy_price, buy_time
)

# 3. 查询持仓时，始终从交易系统获取
holdings = trade_executor.get_holdings(account, C)
position_count = len(holdings)  # 不再从 PositionManager 查
```

#### 卖出流程
```python
# 1. 从交易系统获取真实持仓
holdings = trade_executor.get_holdings(account, C)

# 2. 检查卖出条件（基于元数据）
for stock_code in holdings.keys():
    should_exit, reason = strategy.position_metadata_mgr.check_exit_conditions(
        stock_code, current_prices[stock_code], current_date
    )
    
    if should_exit:
        # 3. 下单时使用交易系统的实际可用数量
        available = holdings[stock_code]['available']
        trade_executor.sell(account, stock_code, price, available, ...)
        
        # 4. 清除元数据
        strategy.position_metadata_mgr.remove_metadata(stock_code)
```

## 优势

### 1. **消除同步问题**
- 持仓数量永远从交易系统查询，不会不一致
- 即使下单失败/部分成交，不影响持仓准确性

### 2. **代码更清晰**
```python
# 之前：需要记住同步
holdings = executor.get_holdings(...)  # 真实持仓
strategy_holdings = strategy.get_holdings()  # 策略持仓（可能不一致！）

# 之后：单一来源
holdings = executor.get_holdings(...)  # 唯一真相
metadata = strategy.metadata_mgr.get_metadata(stock_code)  # 辅助信息
```

### 3. **更符合职责分离**
- **TradeExecutor**：负责交易执行和持仓查询
- **PositionMetadataManager**：负责策略逻辑（得分、目标收益、卖出规则）

### 4. **容错性更好**
- 元数据丢失不影响实际持仓（可以重建）
- 实际持仓是交易系统保证的

## 迁移步骤

### Step 1: 重命名和简化
```bash
# 重命名类
PositionManager → PositionMetadataManager

# 移除字段
- self.holdings[stock_code]['volume']  ✗ 删除
- self.holdings[stock_code]['buy_price']  ✓ 保留
```

### Step 2: 修改调用方
```python
# main_backtest.py / main_realtime.py
- position_count = strategy.get_position_count()
+ position_count = len(trade_executor.get_holdings(...))

- strategy_holdings = strategy.get_holdings()
+ # 不再需要，直接用 trade_executor.get_holdings()
```

### Step 3: 更新 generate_sell_signals
```python
def generate_sell_signals(self, current_prices, current_date, holdings):
    """
    新增参数 holdings：从交易系统传入的实际持仓
    """
    exit_dict = {}
    for stock_code in holdings.keys():  # 遍历真实持仓
        if stock_code in current_prices:
            should_exit, reason = self.metadata_mgr.check_exit_conditions(
                stock_code, current_prices[stock_code], current_date
            )
            if should_exit:
                exit_dict[stock_code] = reason
    return exit_dict
```

## 是否需要自己实现？

**简短回答：需要，但不是持仓管理，是元数据管理**

### 需要保留的部分
```python
✓ calc_position_size()      # 仓位计算逻辑
✓ calc_target_profit()      # 目标收益计算
✓ check_exit_conditions()   # 卖出条件判断
✓ 元数据记录（买入得分、时间等）
```

### 不需要的部分
```python
✗ self.holdings[stock_code]['volume']  # 交易系统已维护
✗ get_all_holdings()                    # 应该从 TradeExecutor 查
✗ get_position_count()                  # 应该从 TradeExecutor 查
✗ get_total_market_value()              # 交易系统有资产查询
```

## 总结

| 维度 | 当前方案 | 推荐方案 |
|------|---------|---------|
| **持仓数量来源** | PositionManager + TradeExecutor | 仅 TradeExecutor |
| **同步问题** | 需要手动 on_buy/on_sell | 无需同步 |
| **数据一致性** | 可能不一致 | 始终一致 |
| **代码复杂度** | 中等（需维护同步逻辑） | 低（单一数据源） |
| **策略元数据** | 混在持仓管理中 | 独立的元数据管理 |

**建议立即重构**，避免后续更大的问题。需要帮你实施重构吗？
