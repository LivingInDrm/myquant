# coding: utf-8

# ========================================
# Strategy Configuration
# 策略参数配置
# ========================================

# ---------- Stock Pool ----------
# STOCK_POOL: 股票池名称
#   - QMT 预定义板块名称，如 '沪深A股', '上证50', '沪深300', '创业板'
#   - 用于策略初始化时获取股票列表
STOCK_POOL = '沪深A股'

# ---------- Buy Conditions ----------
# BUY_CONDITION_1: 买入条件1（连续上涨判断）
BUY_CONDITION_1 = {
    'consecutive_up_days': 5,
    'or_days': 3,
    'or_pct_change': 6.0
}

# BUY_CONDITION_2: 买入条件2（成交量/金额判断）
BUY_CONDITION_2 = {
    'early_volume_ratio': 8,
    'early_amount': 30000000,
    'late_volume_ratio': 3,
    'late_amount': 50000000,
    'early_minutes': 30
}

# ---------- Position Management ----------
# POSITION_SIZE_MAP: 仓位大小映射（根据评分决定仓位比例）
#   - 键: 评分阈值
#   - 值: 仓位比例（占总资金）
POSITION_SIZE_MAP = {
    8: 0.02,
    10: 0.025,
    12: 0.03,
    14: 0.035,
    16: 0.04,
    18: 0.045,
    20: 0.05
}

# TARGET_PROFIT_MAP: 目标收益率映射（根据评分决定止盈点）
#   - 键: 评分阈值
#   - 值: 目标收益率
TARGET_PROFIT_MAP = {
    8: 0.02,
    10: 0.025,
    12: 0.03,
    14: 0.035,
    16: 0.04,
    18: 0.045,
    20: 0.05
}

# ---------- Risk Control ----------
# STOP_LOSS: 止损线（亏损比例）
STOP_LOSS = -0.03

# MAX_HOLD_DAYS: 最大持仓天数
MAX_HOLD_DAYS = 3

# MIN_LISTING_DAYS: 最小上市天数（过滤新股）
MIN_LISTING_DAYS = 120

# MIN_SCORE_THRESHOLD: 最小评分门槛（买入信号筛选）
MIN_SCORE_THRESHOLD = 10

# DEFAULT_POSITION_SIZE: 默认仓位大小（当评分不在映射表中时）
DEFAULT_POSITION_SIZE = 0.02

# DEFAULT_TARGET_PROFIT: 默认止盈点（当评分不在映射表中或元数据缺失时）
DEFAULT_TARGET_PROFIT = 0.02

# ---------- Minute-Level Parameters ----------
# MINUTE_SCAN_ENABLED: 是否启用分钟级扫描
MINUTE_SCAN_ENABLED = True

# DAILY_AVG_VOLUME_WINDOW_5D: 5日平均成交量窗口
DAILY_AVG_VOLUME_WINDOW_5D = 5

# DAILY_AVG_VOLUME_WINDOW_10D: 10日平均成交量窗口
DAILY_AVG_VOLUME_WINDOW_10D = 10

# TRADING_MINUTES_PER_DAY: 每日交易分钟数
TRADING_MINUTES_PER_DAY = 240

# ---------- Slippage (Deprecated - now handled by backtest engine) ----------
# 滑点已统一在 backtest.yaml 中配置 (slippage_type=2, slippage=0.001)
# 策略层不再手动调整价格，避免重复计算滑点
