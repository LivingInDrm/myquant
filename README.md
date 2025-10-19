# 短期强势股量化交易系统

基于 xtquant 实现的短期强势股捕获策略，目标年化收益60%，最大回撤<2%。

## 策略概述

挖掘买入短期强烈上涨标的，持有短期获利卖出。

### 买入条件

同时满足条件1 + 条件2：

**条件1（价格趋势）：**
- 近5个交易日均收盘上涨，或
- 近3个交易日累计上涨 >6%

**条件2（成交量放大）：**
- 开盘半小时内：量比 >8，成交金额 >3000万，或
- 开盘半小时后：量比 >3，成交金额 >5000万

### 上涨趋势确定性得分（8-20分）

| 类别 | 条件 | 得分 |
|------|------|-----|
| 股价突破均线 | 突破5/10/20/30/60日均线 | 各1分 |
| 创新高 | 创20/40/60/80/100日新高 | 各1分 |
| 均线排列 | 短期均线高于长期均线（5组） | 各1分 |
| 成交量放大 | 超过10日均量3/4/5/6/7倍 | 各1分 |

### 仓位管理

| 得分 | 买入仓位 | 目标收益 |
|------|---------|---------|
| 8    | 2%      | 2%      |
| 10   | 2.5%    | 2.5%    |
| 12   | 3%      | 3%      |
| 14   | 3.5%    | 3.5%    |
| 16   | 4%      | 4%      |
| 18   | 4.5%    | 4.5%    |
| 20   | 5%      | 5%      |

### 卖出条件

1. 达成目标收益
2. 止损：跌破成本价 -3%
3. 持仓超期：>3个交易日

---

## 系统架构

```
├── config/                  # 配置文件
│   └── strategy_config.py   # 策略参数
├── core/                    # 核心模块
│   ├── data_provider.py     # 数据层
│   ├── factor_calculator.py # 因子计算
│   ├── position_manager.py  # 仓位管理
│   └── trade_executor.py    # 交易执行
├── strategies/              # 策略
│   └── momentum_strategy.py # 短期强势股策略
├── utils/                   # 工具函数
│   └── helpers.py
├── main_backtest.py         # 回测脚本
└── main_realtime.py         # 实盘脚本
```

---

## 环境要求

- Python 3.6-3.12
- xtquant（QMT提供）
- pandas
- numpy

---

## 安装

1. 确保已安装QMT并启动
2. 安装依赖：

```bash
pip install pandas numpy
```

3. 在QMT中下载历史行情数据

---

## 使用方法

### 1. 配置参数

编辑 `config/strategy_config.py`:

```python
BACKTEST_CONFIG = {
    'initial_capital': 1000000,
    'start_time': '2023-01-01',
    'end_time': '2024-12-31',
    'stock_pool': '沪深A股'
}
```

### 2. 运行回测

```bash
python main_backtest.py
```

### 3. 实盘交易

编辑 `main_realtime.py` 中的配置：

```python
QMT_PATH = r'D:\QMT\userdata_mini'
SESSION_ID = 123456
ACCOUNT_ID = '你的资金账号'
```

运行：

```bash
python main_realtime.py
```

---

## 防止前视偏差

系统严格防止前视偏差：

1. 在 `after_init()` 中预先计算全部因子
2. 所有因子矩阵使用 `.shift(1)` 向后移动一天
3. `handlebar()` 中只使用当前bar之前的数据
4. 买入使用次日开盘价，卖出使用当日开盘价

---

## 批量优化

针对5000+股票：

1. 使用 `get_market_data_ex` 批量获取数据
2. 分批获取（每批500只股票）
3. 使用pandas向量化操作计算因子
4. 避免循环，使用DataFrame批量计算

---

## 回测示例

```python
from xtquant.qmttools import run_strategy_file

param = {
    'stock_code': '000001.SZ',
    'period': '1d',
    'start_time': '2023-01-01',
    'end_time': '2024-12-31',
    'trade_mode': 'backtest',
    'quote_mode': 'history'
}

result = run_strategy_file('main_backtest.py', param=param)

# 查看回测指标
print(result.get_backtest_index())
```

---

## 注意事项

1. **数据准备**：回测前必须在QMT中下载历史数据
2. **股票池**：默认为沪深A股，可在配置中修改
3. **实盘风险**：建议先小资金测试
4. **性能优化**：大股票池可能需要较长计算时间
5. **实时数据**：实盘需要订阅实时行情

---

## 扩展开发

### 添加新策略

1. 在 `strategies/` 下创建新策略类
2. 实现 `prepare_factors()`, `generate_buy_signals()`, `generate_sell_signals()` 方法
3. 在 `main_backtest.py` 中替换策略实例

### 添加新因子

在 `core/factor_calculator.py` 中添加新的因子计算方法。

### 修改仓位规则

编辑 `config/strategy_config.py` 中的 `POSITION_SIZE_MAP` 和 `TARGET_PROFIT_MAP`。

---

## 常见问题

**Q: 回测时提示"无法获取历史数据"？**  
A: 请先在QMT中下载对应时间范围的历史数据。

**Q: 如何调整股票池？**  
A: 修改 `config/strategy_config.py` 中的 `stock_pool` 参数，可选：沪深A股、沪深300、中证500等。

**Q: 如何加快回测速度？**  
A: 减小股票池范围，或使用更小的回测时间范围。

**Q: 实盘如何监控？**  
A: 查看控制台输出，或使用QMT界面查看委托和持仓。

---

## 免责声明

本系统仅供学习研究使用，不构成投资建议。实盘交易有风险，请谨慎使用。

---

## 版本历史

- v1.0.0 (2025-10-18)
  - 初始版本
  - 实现短期强势股策略
  - 支持回测和实盘交易
