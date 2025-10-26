# RQAlpha 数据查看工具

## 数据概览

RQAlpha 已下载的数据包（位置：`C:\Users\LEO\.rqalpha\bundle`）

### 📊 数据统计

| 数据类型 | 数量 | 文件大小 | 日期范围 |
|---------|------|---------|---------|
| **股票** | 5,449 | 1,154.97 MB | 2005-01-04 ~ 2025-10-10 |
| **指数** | 6,381 | 1,336.51 MB | 2005-01-04 ~ 2025-10-10 |
| **期货** | 10,085 | 329.00 MB | 2005-01-04 ~ 各品种到期 |
| **基金** (ETF/LOF/REITs) | 2,260 | 209.14 MB | 2007-07-11 起 |
| **分红数据** | 5,711 | 6.24 MB | 历史分红记录 |
| **交易日历** | 5,346 | 0.04 MB | 2005-01-04 ~ 2026-12-31 |

### 📁 数据文件清单

```
C:\Users\LEO\.rqalpha\bundle\
├── stocks.h5              # 股票日线数据
├── indexes.h5             # 指数日线数据
├── futures.h5             # 期货日线数据
├── funds.h5               # 基金日线数据
├── dividends.h5           # 分红数据
├── split_factor.h5        # 拆股数据
├── ex_cum_factor.h5       # 复权因子
├── suspended_days.h5      # 停牌数据
├── st_stock_days.h5       # ST股票数据
├── yield_curve.h5         # 国债收益率曲线
├── instruments.pk         # 合约信息
├── trading_dates.npy      # 交易日历
├── future_info.json       # 期货交易参数
└── share_transformation.json  # 股票转换信息
```

### 📈 合约类型分布

| 类型 | 数量 | 说明 |
|------|------|------|
| CS (股票) | 5,495 | 普通股票 |
| INDX (指数) | 7,370 | 各类指数 |
| ETF | 1,478 | 交易型开放式基金 |
| Future (期货) | 10,404 | 期货合约 |
| Option (期权) | 168,640 | 期权合约 |
| LOF | 537 | 上市开放式基金 |
| Convertible (可转债) | 1,121 | 可转换债券 |
| FUND (其他基金) | 443 | 其他基金 |

**总计：195,527 个合约**

---

## 🔍 数据查询工具

### 1. 完整数据检查工具

**用途：** 查看 bundle 中所有数据的统计信息

```bash
# 激活环境
.\venv\Scripts\Activate.ps1

# 运行检查脚本
python check_rqalpha_data.py
```

**输出内容：**
- 各类数据文件的大小、数量
- 数据字段结构
- 日期范围
- 示例数据记录

### 2. 快速查询工具

**用途：** 查询特定股票/指数的数据

#### 查询股票数据

```bash
# 查询平安银行全部数据
python query_rqalpha_data.py stock 000001.XSHE

# 查询平安银行2024年数据
python query_rqalpha_data.py stock 000001.XSHE -s 2024-01-01

# 查询平安银行2024年数据，显示前20条
python query_rqalpha_data.py stock 000001.XSHE -s 2024-01-01 -n 20
```

#### 查询指数数据

```bash
# 查询沪深300指数
python query_rqalpha_data.py index 000300.XSHG -s 2024-01-01

# 查询上证指数
python query_rqalpha_data.py index 000001.XSHG -s 2024-01-01
```

#### 搜索合约

```bash
# 搜索包含"平安"的合约
python query_rqalpha_data.py search 平安

# 搜索包含"茅台"的合约
python query_rqalpha_data.py search 茅台

# 搜索股票代码
python query_rqalpha_data.py search 600519
```

#### 列出股票代码

```bash
# 列出所有股票（前50个）
python query_rqalpha_data.py list-stocks

# 列出上证股票（6开头）
python query_rqalpha_data.py list-stocks --prefix 6000 --limit 20

# 列出深证股票（0开头）
python query_rqalpha_data.py list-stocks --prefix 0000 --limit 20

# 列出科创板股票（688开头）
python query_rqalpha_data.py list-stocks --prefix 688 --limit 20
```

#### 列出指数代码

```bash
# 列出所有指数（前50个）
python query_rqalpha_data.py list-indexes

# 列出上证指数
python query_rqalpha_data.py list-indexes --prefix 000
```

---

## 📝 在 RQAlpha 策略中使用数据

### 示例：访问历史数据

```python
from rqalpha.apis import *

def init(context):
    context.s1 = "000001.XSHE"  # 平安银行
    update_universe(context.s1)

def handle_bar(context, bar_dict):
    # 获取最近20天的收盘价
    close_prices = history_bars(context.s1, 20, '1d', 'close')
    
    # 获取当前bar数据
    bar = bar_dict[context.s1]
    logger.info(f"当前价格: {bar.close}")
    
    # 获取多个字段
    bars = history_bars(context.s1, 20, '1d', ['open', 'close', 'high', 'low'])
```

### 示例：获取多个股票数据

```python
def init(context):
    context.stocks = ["000001.XSHE", "600519.XSHG", "600036.XSHG"]
    update_universe(context.stocks)

def handle_bar(context, bar_dict):
    for stock in context.stocks:
        bar = bar_dict[stock]
        logger.info(f"{stock}: {bar.close}")
```

---

## 🔧 常见股票/指数代码

### 主要指数

| 代码 | 名称 |
|------|------|
| 000001.XSHG | 上证指数 |
| 000300.XSHG | 沪深300 |
| 000905.XSHG | 中证500 |
| 000016.XSHG | 上证50 |
| 000852.XSHG | 中证1000 |
| 399001.XSHE | 深证成指 |
| 399006.XSHE | 创业板指 |

### 热门股票示例

| 代码 | 名称 | 市场 |
|------|------|------|
| 000001.XSHE | 平安银行 | 深圳主板 |
| 600519.XSHG | 贵州茅台 | 上海主板 |
| 600036.XSHG | 招商银行 | 上海主板 |
| 000858.XSHE | 五粮液 | 深圳主板 |
| 300750.XSHE | 宁德时代 | 创业板 |
| 688981.XSHG | 中芯国际 | 科创板 |

### 代码规则

| 前缀 | 市场 | 示例 |
|------|------|------|
| 000xxx.XSHE | 深圳主板 | 000001.XSHE |
| 001xxx.XSHE | 深圳主板 | 001979.XSHE |
| 002xxx.XSHE | 中小板 | 002594.XSHE |
| 003xxx.XSHE | 深圳主板 | 003816.XSHE |
| 300xxx.XSHE | 创业板 | 300750.XSHE |
| 600xxx.XSHG | 上海主板 | 600519.XSHG |
| 601xxx.XSHG | 上海主板 | 601318.XSHG |
| 603xxx.XSHG | 上海主板 | 603259.XSHG |
| 688xxx.XSHG | 科创板 | 688981.XSHG |

---

## 📊 数据字段说明

### 股票/指数日线字段

| 字段 | 类型 | 说明 |
|------|------|------|
| datetime | int64 | 日期时间 (20240101000000) |
| open | float64 | 开盘价 |
| close | float64 | 收盘价 |
| high | float64 | 最高价 |
| low | float64 | 最低价 |
| prev_close | float64 | 前收盘价 |
| limit_up | float64 | 涨停价 |
| limit_down | float64 | 跌停价 |
| volume | float64 | 成交量（股） |
| total_turnover | float64 | 成交额（元） |

### 期货日线字段（额外）

| 字段 | 类型 | 说明 |
|------|------|------|
| settlement | float64 | 结算价 |
| prev_settlement | float64 | 前结算价 |
| open_interest | float64 | 持仓量 |

### 分红数据字段

| 字段 | 类型 | 说明 |
|------|------|------|
| book_closure_date | int64 | 股权登记日 |
| announcement_date | float64 | 公告日期 |
| dividend_cash_before_tax | float64 | 税前分红 |
| ex_dividend_date | int64 | 除权除息日 |
| payable_date | int64 | 派息日 |
| round_lot | float64 | 分红单位 |

---

## ⚠️ 注意事项

1. **数据更新周期**
   - 数据包为月度更新
   - 最新数据到 2025-10-10
   - 使用 `rqalpha download-bundle` 更新

2. **数据完整性**
   - 部分股票可能缺少早期数据
   - 退市股票数据保留
   - 停牌日期有记录

3. **编码问题**
   - 中文名称在 Windows 控制台可能显示乱码
   - 不影响数据查询和回测功能
   - 使用代码而非名称进行查询

4. **数据范围**
   - 日线数据：2005-01-04 起
   - 分钟数据：默认 bundle 不包含
   - Tick 数据：默认 bundle 不包含

---

## 🚀 下一步

1. **熟悉数据**
   - 使用查询工具浏览不同股票数据
   - 了解字段含义和数据格式

2. **编写策略**
   - 参考 `RQALPHA_USAGE.md`
   - 使用 `history_bars()` 获取历史数据

3. **回测验证**
   - 选择合适的起止日期
   - 注意数据可用性

4. **接入自有数据**
   - 如需使用 xtquant 数据
   - 参考 `data_source.rst` 实现自定义 DataSource
