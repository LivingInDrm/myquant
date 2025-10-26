# RQAlpha 安装和使用指南

## 1. 安装（已完成）

RQAlpha 已安装到现有 venv 环境：

```bash
# 激活虚拟环境
.\venv\Scripts\Activate.ps1

# 验证安装
rqalpha version
```

当前版本：`0+untagged.3604.gee34889`

## 2. 数据包准备（已完成）

数据包已下载到：`C:\Users\LEO\.rqalpha\bundle`

```bash
# 如需更新数据包（月度更新）
rqalpha download-bundle
```

## 3. 基本命令

### 运行策略

```bash
rqalpha run -f 策略文件.py -s 开始日期 -e 结束日期 -a 账户类型 初始资金
```

**示例：**
```bash
# 运行股票策略
rqalpha run -f .\rqalpha_examples\examples\buy_and_hold.py -s 2020-01-01 -e 2020-12-31 -a stock 100000 --progress

# 运行期货策略
rqalpha run -f .\rqalpha_examples\examples\macd.py -s 2020-01-01 -e 2020-12-31 -a future 100000 --progress

# 运行股票+期货组合
rqalpha run -f strategy.py -s 2020-01-01 -e 2020-12-31 -a stock 100000 -a future 100000
```

### 常用参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `-f, --strategy-file` | 策略文件路径 | `-f strategy.py` |
| `-s, --start-date` | 回测开始日期 | `-s 2020-01-01` |
| `-e, --end-date` | 回测结束日期 | `-e 2020-12-31` |
| `-a, --account` | 账户类型和资金 | `-a stock 100000` |
| `-fq, --frequency` | 回测频率 | `-fq 1d` (日线) / `1m` (分钟) |
| `-bm, --benchmark` | 基准标的 | `-bm 000300.XSHG` |
| `--progress` | 显示进度条 | `--progress` |
| `-o, --output-file` | 输出结果文件 | `-o result.pkl` |
| `--report` | 生成分析报告 | `--report report.xlsx` |
| `-p, --plot` | 绘制图表 | `-p` |

### 查看帮助

```bash
rqalpha --help           # 查看所有命令
rqalpha run --help       # 查看 run 命令参数
rqalpha examples --help  # 查看示例相关命令
```

## 4. 策略示例

### 示例位置

- 源码示例：`.\rqalpha\rqalpha\examples\`
- 本地副本：`.\rqalpha_examples\examples\`

### 可用示例

1. **buy_and_hold.py** - 买入持有策略
2. **golden_cross.py** - 金叉策略
3. **macd.py** - MACD 指标策略（期货）
4. **rsi.py** - RSI 指标策略
5. **turtle.py** - 海龟交易法则
6. **pair_trading.py** - 配对交易

## 5. 策略模板

```python
from rqalpha.apis import *

def init(context):
    # 初始化策略
    context.s1 = "000001.XSHE"  # 股票代码
    update_universe(context.s1)  # 订阅行情
    context.fired = False

def before_trading(context):
    # 每日开盘前执行
    pass

def handle_bar(context, bar_dict):
    # 每个 bar 触发
    if not context.fired:
        # 买入
        order_percent(context.s1, 1)  # 买入该股票至占比100%
        context.fired = True
    
    # 卖出
    # order_target_percent(context.s1, 0)  # 清仓

def after_trading(context):
    # 每日收盘后执行
    pass
```

## 6. 常用 API

### 下单函数

- `order_shares(id_or_ins, amount)` - 按股数下单
- `order_lots(id_or_ins, amount)` - 按手数下单（期货）
- `order_value(id_or_ins, cash_amount)` - 按金额下单
- `order_percent(id_or_ins, percent)` - 按比例买入
- `order_target_percent(id_or_ins, percent)` - 调仓至目标比例
- `order_target_value(id_or_ins, cash_amount)` - 调仓至目标金额

### 数据获取

- `history_bars(order_book_id, bar_count, frequency, fields)` - 获取历史数据
- `current_snapshot(order_book_id)` - 获取当前快照
- `get_price(order_book_id, start_date, end_date)` - 获取价格数据

### 持仓查询

- `context.portfolio` - 投资组合
- `context.portfolio.positions` - 当前持仓
- `context.portfolio.total_value` - 总资产
- `context.portfolio.cash` - 可用资金

## 7. 输出结果

运行后会输出回测结果，包括：

- 总收益率
- 年化收益率
- 夏普比率
- 最大回撤
- 日均成交量
- 等等统计指标

保存结果到文件：

```bash
# 保存 pickle 文件
rqalpha run -f strategy.py -s 2020-01-01 -e 2020-12-31 -a stock 100000 -o result.pkl

# 保存 Excel 报告
rqalpha run -f strategy.py -s 2020-01-01 -e 2020-12-31 -a stock 100000 --report report.xlsx

# 绘制图表
rqalpha run -f strategy.py -s 2020-01-01 -e 2020-12-31 -a stock 100000 -p
```

## 8. 自定义数据源接入

参考文档：`.\rqalpha\docs\source\development\data_source.rst`

### 方式一：策略中直接读取

```python
def init(context):
    import pandas as pd
    import os
    strategy_path = context.config.base.strategy_file
    csv_path = os.path.join(os.path.dirname(strategy_path), "data.csv")
    context.my_data = pd.read_csv(csv_path)
```

### 方式二：创建自定义 DataSource

继承 `BaseDataSource` 并重写关键方法：

```python
from rqalpha.data.base_data_source import BaseDataSource

class MyDataSource(BaseDataSource):
    def get_bar(self, instrument, dt, frequency):
        # 实现自定义数据获取逻辑
        pass
    
    def history_bars(self, instrument, bar_count, frequency, fields, dt, ...):
        # 实现历史数据获取
        pass
    
    def available_data_range(self, frequency):
        from datetime import date
        return date(2020, 1, 1), date.today()
```

详见：`RQALPHA_DATASOURCE.md`（待创建）

## 9. 常见问题

### Q: 提示 "No module named 'rqalpha'"

A: 确保已激活 venv 环境：
```bash
.\venv\Scripts\Activate.ps1
```

### Q: 如何使用分钟线回测？

A: 添加 `-fq 1m` 参数（需要分钟级数据）

### Q: 如何使用自己的行情数据？

A: 参考 `data_source.rst` 创建自定义 DataSource，或在策略中直接读取

### Q: 回测结果如何可视化？

A: 使用 `-p` 参数自动绘图，或使用 `--report` 生成 Excel 报告

## 10. 相关资源

- 官方文档：https://rqalpha.readthedocs.io/
- 源码仓库：https://github.com/ricequant/rqalpha
- 本地文档：`.\rqalpha\docs\`
- 示例代码：`.\rqalpha_examples\examples\`

## 11. 下一步

1. 查看示例策略，了解基本用法
2. 编写自己的策略进行回测
3. 接入自有数据源（如 xtquant）
4. 实盘对接（需要自己实现 Broker）
