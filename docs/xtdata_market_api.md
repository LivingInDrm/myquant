# XtQuant 行情数据 API 文档

> 版本：基于 QMT XtQuant 接口  
> 参考文档：[迅投知识库](https://dict.thinktrader.net/dictionary/stock.html?id=T1H76G)  
> 更新日期：2024-10-18

---

## 📚 目录

1. [API概览](#api概览)
2. [get_market_data - 按字段组织](#get_market_data---按字段组织)
3. [get_market_data_ex - 按股票组织](#get_market_data_ex---按股票组织推荐)
4. [字段说明](#字段说明)
5. [周期说明](#周期说明)
6. [使用场景对比](#使用场景对比)
7. [常见问题](#常见问题)

---

## API概览

XtQuant 提供两个核心行情数据接口：

| 接口 | 数据组织方式 | 推荐场景 | 返回格式 |
|------|------------|---------|---------|
| `get_market_data` | **按字段组织** | 多股票横向对比、因子挖掘 | `{field: DataFrame}` |
| `get_market_data_ex` | **按股票组织** ⭐ | 单股票分析、策略回测、技术指标计算 | `{stock: DataFrame}` |

---

## get_market_data - 按字段组织

### 📖 函数签名

```python
xtdata.get_market_data(
    stock_list=[],           # 股票代码列表
    period='1d',             # 数据周期
    start_time='',           # 开始时间
    end_time='',             # 结束时间
    count=-1,                # 数据条数（-1表示全部）
    dividend_type='none',    # 复权类型
    fill_data=True,          # 是否填充停牌日数据
    field_list=[]            # 字段列表
)
```

### 📋 参数说明

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|-------|------|
| `stock_list` | list[str] | ✅ | `[]` | 股票代码列表，格式：`['600519.SH', '000858.SZ']` |
| `period` | str | ✅ | `'1d'` | 数据周期，见[周期说明](#周期说明) |
| `start_time` | str | ⚠️ | `''` | 开始时间，格式：`'20240101'` 或 `'20240101093000'` |
| `end_time` | str | ⚠️ | `''` | 结束时间，格式同 `start_time` |
| `count` | int | ❌ | `-1` | 获取数据条数，`-1`表示全部（与时间范围二选一） |
| `dividend_type` | str | ❌ | `'none'` | 复权类型：`'none'`不复权, `'front'`前复权, `'back'`后复权 |
| `fill_data` | bool | ❌ | `True` | 是否填充停牌日数据 |
| `field_list` | list[str] | ❌ | `[]` | 字段列表，空列表返回所有字段，见[字段说明](#字段说明) |

> **注意：** `start_time`+`end_time` 和 `count` 二选一使用

### 📤 返回值格式

返回 **字典**，key 为字段名，value 为 **DataFrame**（行=股票代码，列=时间）

```python
{
    'time': DataFrame,      # 时间戳（毫秒）
    'open': DataFrame,      # 开盘价
    'high': DataFrame,      # 最高价
    'low': DataFrame,       # 最低价
    'close': DataFrame,     # 收盘价
    'volume': DataFrame,    # 成交量
    'amount': DataFrame,    # 成交额
    ...
}
```

**DataFrame 结构示例：**

```
data['close']:
              2024-01-01  2024-01-02  2024-01-03  ...
600519.SH        1580.00    1590.00    1600.00
000858.SZ         145.50     146.00     147.20
600036.SH          38.20      38.50      38.80
```

### 💡 使用示例

#### 示例 1：获取多股票日线数据

```python
import xtdata

# 获取多只股票的日线数据
data = xtdata.get_market_data(
    stock_list=['600519.SH', '000858.SZ', '600036.SH'],
    period='1d',
    start_time='20240101',
    end_time='20241018',
    field_list=['time', 'open', 'high', 'low', 'close', 'volume', 'amount']
)

# 访问数据
close_matrix = data['close']  # 获取收盘价矩阵
maotai_close = close_matrix.T['600519.SH']  # 需要转置后才能按股票访问

print("收盘价矩阵：")
print(close_matrix.head())
```

#### 示例 2：多股票相关性分析

```python
# 计算多股票收盘价相关性
close_data = data['close'].T  # 转置：列变为股票代码
correlation = close_data.corr()

print("股票相关性矩阵：")
print(correlation)
```

#### 示例 3：横截面排名（因子分析）

```python
import pandas as pd

# 获取最新交易日的成交量排名
volume_matrix = data['volume']
latest_volume = volume_matrix.iloc[:, -1]  # 最后一列（最新日期）
volume_rank = latest_volume.rank(ascending=False)

print("成交量排名：")
print(volume_rank)
```

### ✅ 适用场景

1. **多股票横向对比**：需要同时比较多只股票的同一指标
2. **因子挖掘**：需要股票×时间的矩阵结构
3. **相关性分析**：计算多股票之间的相关性
4. **横截面分析**：某个时间点上所有股票的排名、分位数等

### ⚠️ 注意事项

- 需要**转置** (`.T`) 才能按股票代码访问数据
- 时间戳为**毫秒级**，需要转换：`pd.to_datetime(time_value, unit='ms')`
- 不适合单股票的时间序列分析

---

## get_market_data_ex - 按股票组织（推荐）

### 📖 函数签名

```python
xtdata.get_market_data_ex(
    stock_list=[],           # 股票代码列表
    period='1d',             # 数据周期
    start_time='',           # 开始时间
    end_time='',             # 结束时间
    count=-1,                # 数据条数（-1表示全部）
    dividend_type='none',    # 复权类型
    fill_data=True,          # 是否填充停牌日数据
    field_list=[]            # 字段列表
)
```

### 📋 参数说明

与 `get_market_data` **完全相同**，参考上方参数表格。

### 📤 返回值格式

返回 **字典**，key 为股票代码，value 为 **DataFrame**（index=时间，columns=字段）

```python
{
    '600519.SH': DataFrame,  # 贵州茅台的数据
    '000858.SZ': DataFrame,  # 五粮液的数据
    '600036.SH': DataFrame,  # 招商银行的数据
    ...
}
```

**DataFrame 结构示例：**

```
data['600519.SH']:
              open     high      low    close      volume       amount
2024-01-01  1580.00  1595.00  1575.00  1590.00  1000000.0  15900000000
2024-01-02  1590.00  1605.00  1588.00  1600.00  1200000.0  19200000000
2024-01-03  1600.00  1620.00  1598.00  1615.00  1100000.0  17765000000
...
```

**特点：**
- ✅ **index 自动设置为时间**（datetime 格式，无需转换）
- ✅ **每只股票独立的 DataFrame**
- ✅ **直接支持 pandas 时间序列操作**

### 💡 使用示例

#### 示例 1：获取单股票日线数据（推荐）

```python
import xtdata

# 获取贵州茅台日线数据
data = xtdata.get_market_data_ex(
    stock_list=['600519.SH'],
    period='1d',
    start_time='20240101',
    end_time='20241018',
    field_list=['open', 'high', 'low', 'close', 'volume', 'amount']
)

# 直接访问数据，无需转置
maotai_df = data['600519.SH']
print(maotai_df.tail(10))

# 直接进行时间序列计算
maotai_df['ma5'] = maotai_df['close'].rolling(5).mean()    # 5日均线
maotai_df['ma20'] = maotai_df['close'].rolling(20).mean()  # 20日均线
maotai_df['return'] = maotai_df['close'].pct_change()      # 日收益率

print("\n技术指标：")
print(maotai_df[['close', 'ma5', 'ma20', 'return']].tail())
```

#### 示例 2：批量处理多只股票

```python
# 批量获取多只股票数据
data = xtdata.get_market_data_ex(
    stock_list=['600519.SH', '000858.SZ', '600036.SH'],
    period='1d',
    start_time='20240101',
    end_time='20241018'
)

# 批量计算技术指标
results = {}
for stock_code, df in data.items():
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    df['signal'] = df['ma5'] > df['ma20']  # 金叉信号
    
    # 统计金叉次数
    signal_count = (df['signal'] & ~df['signal'].shift(1)).sum()
    results[stock_code] = signal_count
    
    print(f"{stock_code} 金叉次数: {signal_count}")
```

#### 示例 3：分钟线数据获取

```python
# 获取5分钟线数据
data_5m = xtdata.get_market_data_ex(
    stock_list=['600519.SH'],
    period='5m',
    start_time='20241001',
    end_time='20241018',
    field_list=['open', 'high', 'low', 'close', 'volume']
)

maotai_5m = data_5m['600519.SH']
print(f"5分钟数据条数: {len(maotai_5m)}")
print(maotai_5m.tail())
```

#### 示例 4：Tick 数据获取

```python
# 获取tick数据（单日）
data_tick = xtdata.get_market_data_ex(
    stock_list=['600519.SH'],
    period='tick',
    start_time='20241018',
    end_time='20241018',
    field_list=['lastPrice', 'volume', 'amount', 'high', 'low']
)

maotai_tick = data_tick['600519.SH']
print(f"Tick数据条数: {len(maotai_tick)}")
print(maotai_tick.head(20))
```

#### 示例 5：使用 count 参数获取最近 N 条数据

```python
# 获取最近100个交易日的数据
data = xtdata.get_market_data_ex(
    stock_list=['600519.SH'],
    period='1d',
    count=100,
    field_list=['close', 'volume']
)

maotai_df = data['600519.SH']
print(f"获取了 {len(maotai_df)} 个交易日的数据")
```

#### 示例 6：前复权数据获取

```python
# 获取前复权数据（消除分红送股影响）
data = xtdata.get_market_data_ex(
    stock_list=['600519.SH'],
    period='1d',
    start_time='20200101',
    end_time='20241018',
    dividend_type='front',  # 前复权
    field_list=['close']
)

maotai_df = data['600519.SH']
print("前复权收盘价：")
print(maotai_df.tail())
```

### ✅ 适用场景（推荐大多数场景）

1. **单股票技术分析**：计算均线、MACD、RSI等指标
2. **策略回测**：每只股票独立回测
3. **时间序列分析**：收益率计算、波动率分析
4. **批量股票处理**：循环处理多只股票
5. **数据导出**：直接保存为CSV等格式
6. **快速原型开发**：符合pandas使用习惯

### ✅ 优势

- ✅ **时间索引自动设置**，无需手动转换
- ✅ **数据结构直观**，符合pandas习惯
- ✅ **代码简洁**，减少数据转换步骤
- ✅ **适合90%的使用场景**

---

## 字段说明

### 通用字段（所有周期）

| 字段名 | 类型 | 说明 | 单位 |
|--------|------|------|------|
| `time` | int64 | 时间戳 | 毫秒（自动转为datetime） |
| `open` | float64 | 开盘价 | 元 |
| `high` | float64 | 最高价 | 元 |
| `low` | float64 | 最低价 | 元 |
| `close` | float64 | 收盘价 | 元 |
| `volume` | float64 | 成交量 | 股 |
| `amount` | float64 | 成交额 | 元 |
| `preClose` | float64 | 前收盘价 | 元 |
| `suspendFlag` | int | 停牌标记（1=停牌，0=正常） | - |

### 日线/分钟线特有字段

| 字段名 | 类型 | 说明 | 适用品种 |
|--------|------|------|----------|
| `settle` | float64 | 结算价 | 期货 |
| `openInterest` | float64 | 持仓量 | 期货 |

### Tick 特有字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `time` | int64 | 时间戳（毫秒） |
| `stime` | string | 时间戳字符串（YYYYMMDDHHmmss） |
| `lastPrice` | float64 | 最新价 |
| `open` | float64 | 开盘价 |
| `high` | float64 | 最高价 |
| `low` | float64 | 最低价 |
| `lastClose` | float64 | 前收盘价 |
| `amount` | float64 | 成交总额 |
| `volume` | int | 成交总量（手） |
| `pvolume` | int | 原始成交总量（未经过股手转换） |
| `stockStatus` | int | 证券状态 |
| `openInterest` | int | 若为股票则代表证券状态，非股票代表持仓量 |
| `openInt` | float64 | 同 openInterest（历史别名，含义同上） |
| `transactionNum` | float | 成交笔数（期货无，单独计算） |
| `lastSettlementPrice` | float64 | 前结算（股票为0） |
| `settlementPrice` | float64 | 今结算（股票为0） |
| `askPrice` | list[float] | 多档委卖价 |
| `askVol` | list[int] | 多档委卖量 |
| `bidPrice` | list[float] | 多档委买价 |
| `bidVol` | list[int] | 多档委买量 |

### 字段使用示例

```python
# 获取所有字段
data = xtdata.get_market_data_ex(
    stock_list=['600519.SH'],
    period='1d',
    count=10,
    field_list=[]  # 空列表返回所有可用字段
)

# 查看所有列名
print(data['600519.SH'].columns.tolist())

# 获取指定字段
data = xtdata.get_market_data_ex(
    stock_list=['600519.SH'],
    period='1d',
    count=10,
    field_list=['close', 'volume']  # 只获取收盘价和成交量
)
```

---

## 周期说明

### 支持的周期类型

| 周期代码 | 说明 | 适用场景 | 数据量 |
|---------|------|---------|--------|
| `'tick'` | 逐笔成交 | 高频交易、订单流分析 | 极大 ⚠️ |
| `'1m'` | 1分钟线 | 日内交易 | 大 |
| `'5m'` | 5分钟线 | 日内交易 | 中 |
| `'15m'` | 15分钟线 | 短线交易 | 中 |
| `'30m'` | 30分钟线 | 短线交易 | 中 |
| `'60m'` / `'1h'` | 60分钟线 | 短线交易 | 小 |
| `'1d'` | 日线 | 中长期交易 | 小 ✅ |
| `'1w'` | 周线 | 中长期分析 | 极小 |
| `'1mon'` | 月线 | 长期分析 | 极小 |
| `'1q'` | 季线 | 长期分析 | 极小 |
| `'1hy'` | 半年线 | 长期分析 | 极小 |
| `'1y'` | 年线 | 长期分析 | 极小 |

### 专题周期（扩展）

- `stoppricedata`：历史涨跌停价格
  - 使用方式：先 `xtdata.download_history_data(code, 'stoppricedata')`，再 `get_market_data_ex([], [code], 'stoppricedata', ...)`
  - 说明：可用 `count`、`start_time/end_time` 组合筛选；VIP 数据
- `snapshotindex`：股票快照指标（量比、涨速、换手等）
  - 使用方式：需先 `subscribe_quote(code, period='snapshotindex')` 再取；VIP 数据
- `limitupperformance`：涨跌停/集合竞价表现
  - 使用方式：先下载历史（如 `download_history_data2`），并订阅 `period='limitupperformance'`；VIP 数据
- `transactioncount1d`/`transactioncount1m`：资金流向聚合
  - 使用方式：先下载历史 `download_history_data(code, 'transactioncount1d')` 等；VIP 数据
- `orderflow1m`/`5m`/`15m`/`30m`/`1h`/`1d`：订单流
  - 使用方式：仅 `orderflow1m` 提供历史下载，其它周期基于 1m 合成；需先下载 `orderflow1m`；订单流版权限
- `interactiveqa`：问董秘数据
  - 使用方式：先下载 `download_history_data(code, 'interactiveqa')`；VIP 数据
- `announcement`：交易所公告
  - 使用方式：先下载 `download_history_data(code, 'announcement')`；VIP 数据
- `northfinancechange1m`/`northfinancechange1d`：北向/南向数据
  - 使用方式：先下载对应周期；标的可用特殊代码如 `FFFFFF.SGT`；VIP 数据

### 时间格式要求

| 周期 | 时间格式 | 示例 |
|------|---------|------|
| 日线及以上 | `'YYYYMMDD'` | `'20240101'` |
| 分钟线 | `'YYYYMMDD'` 或 `'YYYYMMDDHHmmss'` | `'20240101093000'` |
| Tick | `'YYYYMMDD'` 或 `'YYYYMMDDHHmmss'` | `'20240101093000'` |

### 周期使用建议

```python
# ✅ 推荐：日线数据，时间跨度可以较长
data_1d = xtdata.get_market_data_ex(
    stock_list=['600519.SH'],
    period='1d',
    start_time='20200101',  # 可以几年
    end_time='20241018'
)

# ⚠️ 注意：分钟线数据量大，建议时间跨度不超过1个月
data_5m = xtdata.get_market_data_ex(
    stock_list=['600519.SH'],
    period='5m',
    start_time='20241001',  # 建议不超过1个月
    end_time='20241018'
)

# ⚠️ 警告：Tick数据量极大，建议单次不超过1-2天
data_tick = xtdata.get_market_data_ex(
    stock_list=['600519.SH'],
    period='tick',
    start_time='20241018',  # 建议单日
    end_time='20241018'
)
```

---

## 使用场景对比

### 场景对比表

| 使用场景 | `get_market_data` | `get_market_data_ex` | 推荐 |
|---------|-------------------|---------------------|------|
| 单股票技术分析 | ❌ 需要转置 | ✅ 直接使用 | ⭐ Ex |
| 计算技术指标（均线、MACD等） | ❌ 数据转换复杂 | ✅ 一行代码 | ⭐ Ex |
| 策略回测 | ❌ 数据结构不便 | ✅ 完美支持 | ⭐ Ex |
| 多股票收益率对比 | ✅ 横向对比方便 | ⚠️ 需要合并 | Normal |
| 因子挖掘（横截面） | ✅ 天然矩阵结构 | ❌ 需要重组 | Normal |
| 相关性分析 | ✅ 直接计算 | ⚠️ 需要转换 | Normal |
| 批量处理多只股票 | ❌ 循环转置麻烦 | ✅ 简单循环 | ⭐ Ex |
| 数据导出CSV | ❌ 需要转换 | ✅ 直接导出 | ⭐ Ex |
| pandas时间序列操作 | ❌ 不支持 | ✅ 完美支持 | ⭐ Ex |

### 决策树

```
需要获取行情数据？
  ├─ 是否需要多股票横向对比同一指标？
  │   ├─ 是 → 使用 get_market_data
  │   └─ 否 ↓
  │
  ├─ 是否需要计算技术指标？
  │   ├─ 是 → 使用 get_market_data_ex ⭐
  │   └─ 否 ↓
  │
  ├─ 是否需要策略回测？
  │   ├─ 是 → 使用 get_market_data_ex ⭐
  │   └─ 否 ↓
  │
  ├─ 是否需要因子挖掘（矩阵操作）？
  │   ├─ 是 → 使用 get_market_data
  │   └─ 否 ↓
  │
  └─ 默认推荐 → 使用 get_market_data_ex ⭐
```

---

## 常见问题

### Q1: 两个接口可以互相转换吗？

**A:** 可以，通过简单的数据转换：

```python
# get_market_data → get_market_data_ex 格式
def convert_to_ex_format(data, stock_code):
    """将 get_market_data 格式转为 get_market_data_ex 格式"""
    import pandas as pd
    
    df = pd.DataFrame()
    for field in data.keys():
        if field == 'time':
            df.index = pd.to_datetime(data['time'].T[stock_code], unit='ms')
        else:
            df[field] = data[field].T[stock_code].values
    return df

# 使用示例
data_normal = xtdata.get_market_data(['600519.SH'], '1d', count=10)
df_ex_format = convert_to_ex_format(data_normal, '600519.SH')
```

### Q2: 为什么推荐使用 get_market_data_ex？

**A:** 主要原因：
1. ✅ **自动时间索引**，无需手动转换
2. ✅ **符合pandas习惯**，代码更简洁
3. ✅ **适合90%的场景**，特别是技术分析和回测
4. ✅ **减少数据转换步骤**，降低出错概率

### Q3: get_market_data 什么时候用？

**A:** 仅在以下场景推荐：
- 需要**多股票横截面分析**（如因子排名）
- 需要直接的**股票×时间矩阵**结构
- 计算多股票的**相关性矩阵**

### Q4: 时间参数和 count 参数如何选择？

**A:** 
- **时间参数**（`start_time` + `end_time`）：明确知道时间范围
- **count 参数**：需要最近N条数据，不关心具体日期

```python
# 方式1：使用时间参数（推荐用于固定时间范围）
data = xtdata.get_market_data_ex(
    stock_list=['600519.SH'],
    period='1d',
    start_time='20240101',
    end_time='20241018'
)

# 方式2：使用count参数（推荐用于滚动窗口）
data = xtdata.get_market_data_ex(
    stock_list=['600519.SH'],
    period='1d',
    count=100  # 最近100个交易日
)
```

### Q5: 复权类型如何选择？

**A:**

| 复权类型 | 参数值 | 适用场景 | 说明 |
|---------|--------|---------|------|
| 不复权 | `'none'` | 实时交易 | 真实价格，但有跳空 |
| 前复权 | `'front'` | 技术分析、回测 ⭐ | 当前价格不变，历史价格调整 |
| 后复权 | `'back'` | 收益率分析 | 历史价格不变，当前价格调整 |

**推荐：大多数情况使用前复权 `'front'`**

```python
# 前复权：适合技术分析和策略回测
data = xtdata.get_market_data_ex(
    stock_list=['600519.SH'],
    period='1d',
    start_time='20200101',
    end_time='20241018',
    dividend_type='front'  # 前复权
)
```

### Q6: 如何处理停牌数据？

**A:** 使用 `fill_data` 参数：

```python
# 填充停牌日数据（默认）
data = xtdata.get_market_data_ex(
    stock_list=['600519.SH'],
    period='1d',
    count=100,
    fill_data=True  # 停牌日填充前一交易日数据
)

# 不填充停牌日（实际交易日）
data = xtdata.get_market_data_ex(
    stock_list=['600519.SH'],
    period='1d',
    count=100,
    fill_data=False  # 只返回实际交易日
)
```

### Q7: 数据获取失败怎么办？

**A:** 常见原因及解决方法：

1. **QMT客户端未启动**
   ```bash
   # 解决：启动QMT客户端
   ```

2. **数据未下载到本地**
   ```python
   # 解决：先订阅数据
   xtdata.subscribe_quote('600519.SH', period='1d', count=-1)
   xtdata.run()  # 下载数据
   ```

3. **股票代码格式错误**
   ```python
   # ❌ 错误
   data = xtdata.get_market_data_ex(['600519'], '1d', count=10)
   
   # ✅ 正确
   data = xtdata.get_market_data_ex(['600519.SH'], '1d', count=10)
   ```

### Q8: 如何批量获取多只股票并保存？

**A:**

```python
import xtdata
import pandas as pd
import os

# 批量获取
stock_list = ['600519.SH', '000858.SZ', '600036.SH', '601318.SH']
data = xtdata.get_market_data_ex(
    stock_list=stock_list,
    period='1d',
    start_time='20240101',
    end_time='20241018',
    dividend_type='front'
)

# 批量保存
output_dir = 'data/stocks'
os.makedirs(output_dir, exist_ok=True)

for stock_code, df in data.items():
    # 提取股票代码（去除市场后缀）
    stock_name = stock_code.split('.')[0]
    output_file = os.path.join(output_dir, f'{stock_name}.csv')
    
    # 保存为CSV
    df.to_csv(output_file, encoding='utf-8-sig')
    print(f"已保存: {output_file}")
```
```

### Q9: 如何同时获取历史+最新行情（自动拼接）？

**A:** 步骤如下：

1) 先下载历史数据（仅历史从本地读取）
```python
xtdata.download_history_data('600519.SH', period='1d', start_time='20240101', end_time='')
```

2) 订阅最新行情（最新从服务器返回）
```python
xtdata.subscribe_quote('600519.SH', period='1d')
```

3) 获取数据（自动拼接历史+最新）
```python
data = xtdata.get_market_data_ex(
    stock_list=['600519.SH'],
    period='1d',
    start_time='20240101',
    end_time='',
    count=-1  # -1 表示全部，返回历史+最新
)
df = data['600519.SH']
```

> 说明：`get_market_data_ex` 无 `subscribe` 参数，如需最新数据，必须先调用 `subscribe_quote`。只取历史可不订阅。

### Q10: `count` 与 `start_time/end_time` 的关系是什么？

**A:** 规则如下：

- 同时给出 `start_time` 和 `end_time` 且 `count >= 0` 时：以 `end_time` 为基准，向前取 `count` 条。
- `start_time` 与 `end_time` 缺省，且 `count >= 0`：返回本地最新的 `count` 条数据。
- `start_time`、`end_time`、`count` 都缺省，或 `count == -1`：返回本地全部数据（若已订阅则含最新拼接）。
- 分钟/Tick 数据量较大，建议缩短时间范围或使用 `count` 控制条数。

### Q11: 为什么 `get_market_data_ex` 有时拿不到最新数据？

**A:** 因为 `get_market_data_ex` 不带订阅开关。要拿到“最新”必须先订阅：

```python
xtdata.subscribe_quote('600519.SH', period='1d')
data = xtdata.get_market_data_ex(['600519.SH'], '1d', count=1)
```

未订阅时只会返回本地已有历史。需要历史+最新，先下载历史，再订阅，最后调用获取接口。

---

## 完整示例：技术分析系统

```python
"""
完整示例：使用 get_market_data_ex 构建技术分析系统
"""
import xtdata
import pandas as pd
import numpy as np

class TechnicalAnalyzer:
    """技术分析器"""
    
    def __init__(self, stock_code, start_date, end_date):
        """初始化"""
        self.stock_code = stock_code
        self.start_date = start_date
        self.end_date = end_date
        self.data = None
        
    def load_data(self):
        """加载数据"""
        data = xtdata.get_market_data_ex(
            stock_list=[self.stock_code],
            period='1d',
            start_time=self.start_date,
            end_time=self.end_date,
            dividend_type='front',
            field_list=['open', 'high', 'low', 'close', 'volume', 'amount']
        )
        self.data = data[self.stock_code]
        return self
    
    def add_ma(self, periods=[5, 10, 20, 60]):
        """计算移动平均线"""
        for period in periods:
            self.data[f'ma{period}'] = self.data['close'].rolling(period).mean()
        return self
    
    def add_macd(self, fast=12, slow=26, signal=9):
        """计算MACD"""
        ema_fast = self.data['close'].ewm(span=fast).mean()
        ema_slow = self.data['close'].ewm(span=slow).mean()
        self.data['macd'] = ema_fast - ema_slow
        self.data['macd_signal'] = self.data['macd'].ewm(span=signal).mean()
        self.data['macd_hist'] = self.data['macd'] - self.data['macd_signal']
        return self
    
    def add_rsi(self, period=14):
        """计算RSI"""
        delta = self.data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        self.data['rsi'] = 100 - (100 / (1 + rs))
        return self
    
    def add_bollinger_bands(self, period=20, std=2):
        """计算布林带"""
        ma = self.data['close'].rolling(period).mean()
        std_dev = self.data['close'].rolling(period).std()
        self.data['bb_upper'] = ma + (std_dev * std)
        self.data['bb_middle'] = ma
        self.data['bb_lower'] = ma - (std_dev * std)
        return self
    
    def generate_signals(self):
        """生成交易信号"""
        # 金叉信号：短期均线上穿长期均线
        self.data['golden_cross'] = (
            (self.data['ma5'] > self.data['ma20']) & 
            (self.data['ma5'].shift(1) <= self.data['ma20'].shift(1))
        )
        
        # 死叉信号：短期均线下穿长期均线
        self.data['death_cross'] = (
            (self.data['ma5'] < self.data['ma20']) & 
            (self.data['ma5'].shift(1) >= self.data['ma20'].shift(1))
        )
        
        # MACD金叉
        self.data['macd_golden'] = (
            (self.data['macd'] > self.data['macd_signal']) & 
            (self.data['macd'].shift(1) <= self.data['macd_signal'].shift(1))
        )
        
        return self
    
    def get_latest_analysis(self):
        """获取最新分析结果"""
        latest = self.data.iloc[-1]
        
        analysis = {
            '股票代码': self.stock_code,
            '最新价': f"{latest['close']:.2f}",
            'MA5': f"{latest['ma5']:.2f}",
            'MA20': f"{latest['ma20']:.2f}",
            'MACD': f"{latest['macd']:.2f}",
            'RSI': f"{latest['rsi']:.2f}",
            '布林带上轨': f"{latest['bb_upper']:.2f}",
            '布林带下轨': f"{latest['bb_lower']:.2f}",
        }
        
        return analysis

# 使用示例
if __name__ == '__main__':
    # 分析贵州茅台
    analyzer = TechnicalAnalyzer(
        stock_code='600519.SH',
        start_date='20230101',
        end_date='20241018'
    )
    
    # 加载数据并计算指标
    analyzer.load_data() \
           .add_ma() \
           .add_macd() \
           .add_rsi() \
           .add_bollinger_bands() \
           .generate_signals()
    
    # 查看最新分析
    analysis = analyzer.get_latest_analysis()
    print("技术分析结果：")
    for key, value in analysis.items():
        print(f"{key}: {value}")
    
    # 查看最近的交易信号
    signals = analyzer.data[
        analyzer.data['golden_cross'] | 
        analyzer.data['death_cross']
    ][['close', 'ma5', 'ma20', 'golden_cross', 'death_cross']].tail(10)
    
    print("\n最近的交易信号：")
    print(signals)
    
    # 保存完整数据
    analyzer.data.to_csv('data/technical_analysis.csv', encoding='utf-8-sig')
    print("\n数据已保存到: data/technical_analysis.csv")
```

---

## 总结

### 快速选择指南

**🎯 90%的场景请使用 `get_market_data_ex`**

- ✅ 单股票分析
- ✅ 技术指标计算
- ✅ 策略回测
- ✅ 批量处理

**🎯 仅在以下场景使用 `get_market_data`**

- ✅ 多股票横截面对比
- ✅ 因子挖掘（需要矩阵）
- ✅ 相关性分析

### 最佳实践

1. **优先使用 `get_market_data_ex`**，代码更简洁
2. **使用前复权数据** (`dividend_type='front'`)
3. **合理设置时间范围**，避免数据量过大
4. **Tick数据单次获取不超过1-2天**
5. **分钟线数据建议不超过1个月**
6. **使用 `count` 参数获取固定条数**更灵活

---

**文档版本：** v1.0  
**最后更新：** 2024-10-18  
**作者：** AI Assistant  
**适用版本：** QMT XtQuant

