# Lesson Learned

## 2025-10-20: A股回测T+1规则缺失

### 问题
卖出逻辑使用 `holding['volume']`（总持仓）而非 `holding['available']`（可用数量），导致当天买入的股票可以立即卖出，违反A股T+1规则。

### 根本原因
QMT回测引擎的持仓数据包含两个字段:
- `m_nVolume`: 总持仓数量
- `m_nCanUseVolume`: 可用数量（当天买入=0）

代码未检查可用数量，直接使用总持仓。

### 修复
```python
# 错误
volume = holding['volume']

# 正确
available_volume = holding.get('available', 0)
if available_volume <= 0:
    continue  # T+1限制
```

### 教训
- 回测必须严格遵守市场规则（T+1、涨跌停、手续费）
- 使用交易所提供的可用数量字段，不要自己计算

---

## 2025-10-20: 持仓数据源不一致

### 问题
策略内部 (`PositionManager.holdings`) 和回测引擎 (`get_trade_detail_data`) 维护两套独立持仓，导致:
- 卖出信号基于策略内部持仓
- 卖出执行检查回测引擎持仓
- 数据不一致导致卖出失败

### 修复
统一使用单一数据源，推荐使用策略内部持仓:
```python
current_holdings = g.strategy.get_holdings()  # 而非 g.trade_executor.get_holdings()
```

### 教训
- **单一数据源原则**: 持仓查询、买卖检查必须使用同一来源
- 避免"双重记账"，状态同步成本高且易出错

---

## 2025-10-20: QMT回测持仓查询延迟

### 问题
`passorder` 下单后立即查询持仓，数据未更新，导致重复买入:
```
[09:30] 买入 603948.SH: 数量=700
[09:31] 买入 603948.SH: 数量=700  # 重复
```

### 根本原因
`get_trade_detail_data` 返回分钟开始时的快照，同一bar内多次查询返回相同结果。

### 修复
在策略层维护已下单状态:
```python
g.strategy.on_buy(stock_code, ...)
existing_codes = set(g.strategy.get_holdings().keys())
```

### 教训
- 回测引擎的查询API可能有延迟，不要假设实时性
- 关键状态需在策略层自行维护

---

## 2025-10-20: 调试日志原则

### 关键点
操作前后打印状态变化:
```python
print(f"[DEBUG] 操作前: {state_before}")
result = operation()
print(f"[DEBUG] 返回值: {result}")
print(f"[DEBUG] 操作后: {state_after}")
```

### 教训
- 关键分支必须有日志（买入、卖出、持仓变化）
- 不假设API行为，用日志验证
- 记录关键字段：总数量、可用数量、order_id、持仓数
