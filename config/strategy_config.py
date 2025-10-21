# coding: utf-8

BUY_CONDITION_1 = {
    'consecutive_up_days': 5,
    'or_days': 3,
    'or_pct_change': 6.0
}

BUY_CONDITION_2 = {
    'early_volume_ratio': 8,
    'early_amount': 30000000,
    'late_volume_ratio': 1.5,
    'late_amount': 10000000,
    'early_minutes': 30
}

POSITION_SIZE_MAP = {
    8: 0.02,
    10: 0.025,
    12: 0.03,
    14: 0.035,
    16: 0.04,
    18: 0.045,
    20: 0.05
}

TARGET_PROFIT_MAP = {
    8: 0.02,
    10: 0.025,
    12: 0.03,
    14: 0.035,
    16: 0.04,
    18: 0.045,
    20: 0.05
}

STOP_LOSS = -0.03
MAX_HOLD_DAYS = 3
MIN_LISTING_DAYS = 120
MAX_POSITIONS = 20

MINUTE_SCAN_ENABLED = True
DAILY_AVG_VOLUME_WINDOW_5D = 5
DAILY_AVG_VOLUME_WINDOW_10D = 10
TRADING_MINUTES_PER_DAY = 240

SLIPPAGE_BUY = 0.005
SLIPPAGE_SELL = 0.005

BACKTEST_CONFIG = {
    'initial_capital': 1000000,
    'start_time': '2025-09-01',
    'end_time': '2025-09-02',
    'stock_pool': '沪深A股'
}
