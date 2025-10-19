## 目标

将当前一次性处理全天数据的handlebar逻辑，重构为每分钟触发一次、仅处理当前bar数据的标准量化架构。

---

## 核心改动

### 1. 回测参数调整（main_backtest.py）

**位置**: `main_backtest.py` 底部 `if __name__ == '__main__'` 块

**改动**:
- `period` 从 `'1d'` 改为 `'1m'`
- 保持 `stock_code` 为基准合约（'000001.SZ'）

---

### 2. 数据预加载架构（after_init函数）

**位置**: `main_backtest.py:71-130`

**新增逻辑**:
- 预加载回测期间所有交易日的1分钟数据
- 存储在 `g.minute_data_cache` 中，结构：`{date: {stock_code: DataFrame}}`
- 保持现有的日频因子计算不变（用于condition1和日频过滤）

**实现方式**:
```
1. 获取回测期间的交易日列表
2. 循环每个交易日，调用 data_provider.get_minute_data()
3. 存储到 g.minute_data_cache[date]
```

---

### 3. 全局状态管理（init函数）

**位置**: `main_backtest.py:38-68`

**新增字段** (在 `g` 对象中):
- `g.current_trading_date`: 当前交易日（YYYYMMDD格式）
- `g.intraday_state`: 日内状态字典
  - `open_sell_done`: bool，是否已执行开盘卖出
  - `buy_count_today`: int，当日买入次数
  - `cum_volumes`: dict，累计成交量 {stock_code: volume}
  - `cum_amounts`: dict，累计成交额 {stock_code: amount}

---

### 4. handlebar重构（核心逻辑）

**位置**: `main_backtest.py:132-359`

**重构原则**: 每次调用仅处理当前1分钟bar

#### 4.1 识别当前bar信息
- 获取当前bar的时间戳（C.get_bar_timetag）
- 解析出日期和分钟时间
- 判断是否为交易日的第一个bar（9:31）

#### 4.2 交易日切换逻辑
**触发条件**: 当前bar日期 != g.current_trading_date

**执行**:
- 检查日期是否在回测范围内，不在则return
- 打印交易日分隔线
- 执行开盘卖出逻辑（卖出上一日持仓）
- 重置日内状态：
  ```python
  g.intraday_state = {
      'open_sell_done': True,
      'buy_count_today': 0,
      'cum_volumes': {},
      'cum_amounts': {}
  }
  ```
- 初始化策略分钟缓存：`g.strategy.init_minute_cache(current_date, g.stock_list)`
- 更新 `g.current_trading_date`

#### 4.3 当前bar数据提取
- 从 `g.minute_data_cache[current_date]` 中提取当前时间戳的数据
- 构建 `minute_prices`, `minute_volumes`, `minute_amounts` 字典

#### 4.4 更新日内累计状态
- 遍历 `minute_prices.keys()`
- 更新 `g.intraday_state['cum_volumes'][stock_code] += volume`
- 更新 `g.intraday_state['cum_amounts'][stock_code] += amount`

#### 4.5 更新分钟因子
- 调用 `g.strategy.update_minute_factors()`
- 传入当前bar的价格、成交量、成交额

#### 4.6 生成买入信号并执行
- 调用 `g.strategy.generate_buy_signals_minute(current_date)`
- 检查持仓空位和资金
- 遍历买入信号，执行买入
- 更新 `g.intraday_state['buy_count_today']`

#### 4.7 移除的逻辑
- ❌ 删除全天时间戳的循环（line 220-324）
- ❌ 删除"分钟级扫描完成"总结（line 325）

---

### 5. 策略类调整（momentum_strategy.py）

**位置**: `strategies/momentum_strategy.py`

**改动**:
- `init_minute_cache`: 调整初始化逻辑，将 `cum_volume` 和 `cum_amount` 改为从 `g.intraday_state` 读取
- `update_minute_factors`: 确保累计量从外部传入或从 `g` 读取（由主逻辑管理）

**可选优化**:
- 如果策略需要访问全局状态，可以在构造函数中接受 `g` 的引用

---

### 6. 调试和验证点

**关键日志输出**:
1. 每个交易日第一个bar：打印交易日、开盘卖出数量
2. 首个10分钟内：每分钟打印 cond1/cond2 满足数、买入信号数
3. 发生买入时：打印时间戳、股票代码、价格、数量
4. 交易日结束：不再需要（因为没有"全天扫描完成"的概念）

**验证逻辑**:
- 确认每个交易日的第一个bar会触发开盘卖出
- 确认日内累计量在跨bar时正确累加
- 确认买入发生在正确的分钟bar上

---

## 架构优势

### 改造前（当前）
```
handlebar (每日调用1次)
  ├─ 获取全天1分钟数据
  ├─ for timestamp in timestamps:  # 240次循环
  │    ├─ 更新因子
  │    ├─ 生成信号
  │    └─ 执行买入
  └─ 完成
```

### 改造后（目标）
```
handlebar (每分钟调用1次)
  ├─ if 交易日切换: 开盘卖出 + 重置状态
  ├─ 提取当前bar数据
  ├─ 更新累计量
  ├─ 更新分钟因子
  ├─ 生成买入信号
  └─ 执行买入
```

---

## 关键依赖

- `C.get_bar_timetag(C.barpos)`: 获取当前bar时间戳
- `g.minute_data_cache`: 预加载的分钟数据
- `g.intraday_state`: 日内状态保持

---

## 风险和约束

1. **QMT回测框架约束**: 确保 `period='1m'` 时，QMT会按预期每分钟调用 handlebar
2. **内存消耗**: 预加载所有1分钟数据可能消耗较多内存（回测期长时）
3. **开盘卖出时机**: 在交易日第一个bar执行，使用前一日收盘价或当日开盘价需明确
4. **状态持久化**: 确保 `g` 对象在整个回测期间保持状态

---

## 文件清单

- `main_backtest.py`: 主要改动文件
- `strategies/momentum_strategy.py`: 轻微调整
- `core/data_provider.py`: 无需改动（已有 get_minute_data）
- `config/strategy_config.py`: 无需改动
