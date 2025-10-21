# coding: utf-8
import sys
import io
import os

os.environ['PYTHONIOENCODING'] = 'utf-8'

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)

import pandas as pd
import numpy as np
from datetime import datetime
from xtquant import xtdata

from core.data_provider import DataProvider
from core.trade_executor import TradeExecutor
from strategies.momentum_strategy import MomentumStrategy
from utils.helpers import get_df_ex, filter_opendate, timetag_to_datetime
from config.strategy_config import BACKTEST_CONFIG, MAX_POSITIONS, SLIPPAGE_BUY, SLIPPAGE_SELL


class G:
    """全局变量容器"""
    pass


g = G()


def init(C):
    """
    初始化函数
    
    Args:
        C: contextinfo对象
    """
    print("=" * 60)
    print("初始化短期强势股量化交易系统")
    print("=" * 60)
    
    g.stock_pool_name = BACKTEST_CONFIG.get('stock_pool', '沪深A股')
    g.initial_capital = BACKTEST_CONFIG.get('initial_capital', 1000000)
    
    g.data_provider = DataProvider(batch_size=500)
    g.trade_executor = TradeExecutor(mode='backtest')
    g.strategy = MomentumStrategy()
    
    g.stock_list = C.get_stock_list_in_sector(g.stock_pool_name)
    print(f"股票池: {g.stock_pool_name}, 股票数量: {len(g.stock_list)}")
    
    g.account_id = 'test'
    g.money = 1000000
    
    g.max_buy_count = MAX_POSITIONS
    
    g.minute_data_cache = {}
    g.current_trading_date = None
    g.day_state = {
        'buy_count': 0,
        'minute_counter': 0,
        'last_signal_count': 0,
        'open_prices': {}
    }
    
    print(f"[DEBUG] 账户ID: {g.account_id}")
    print(f"[DEBUG] 初始资金设置: {g.money}")
    print(f"[DEBUG] 回测配置: {BACKTEST_CONFIG}")
    
    print("初始化完成")


def after_init(C):
    """
    初始化后处理，预先计算所有因子
    
    Args:
        C: contextinfo对象
    """
    print("=" * 60)
    print("开始预处理数据和计算因子")
    print("=" * 60)
    
    start_time = BACKTEST_CONFIG['start_time'].replace('-', '')
    end_time = BACKTEST_CONFIG['end_time'].replace('-', '')
    
    warmup_days = 365
    data_start_time = pd.to_datetime(start_time) - pd.Timedelta(days=warmup_days)
    data_start_time_str = data_start_time.strftime('%Y%m%d')
    
    print(f"回测执行范围: {start_time} ~ {end_time}")
    print(f"数据获取范围: {data_start_time_str} ~ {end_time} (包含{warmup_days}天热身期)")
    print(f"正在获取 {len(g.stock_list)} 只股票的历史数据...")
    
    g.backtest_start = start_time
    g.backtest_end = end_time
    
    data = g.data_provider.get_daily_data(
        stock_list=g.stock_list,
        start_time=data_start_time_str,
        end_time=end_time,
        dividend_type='front',
        fill_data=True
    )
    
    if not data:
        print("错误：无法获取历史数据")
        return
    
    print("转换数据格式...")
    close_df = get_df_ex(data, 'close')
    open_df = get_df_ex(data, 'open')
    high_df = get_df_ex(data, 'high')
    volume_df = get_df_ex(data, 'volume')
    amount_df = get_df_ex(data, 'amount')
    
    print(f"数据时间范围: {close_df.index[0]} ~ {close_df.index[-1]}")
    print(f"数据维度: {close_df.shape}")
    
    print("计算上市日期过滤...")
    listing_filter_df = filter_opendate(g.stock_list, close_df, 120, 'xtdata')
    
    g.strategy.prepare_daily_factors(
        close_df, open_df, high_df, volume_df, amount_df,
        stock_list=g.stock_list,
        listing_filter_df=listing_filter_df
    )
    
    print("=" * 60)
    print("数据预处理完成，开始回测")
    print("=" * 60)


def start_new_trading_day(current_date, C):
    """
    交易日切换处理
    
    Args:
        current_date: 当前交易日（字符串格式，如'20240115'）
        C: contextinfo对象
    """
    print(f"\n{'=' * 60}")
    print(f"新交易日: {current_date}")
    print(f"{'=' * 60}")
    
    print(f"加载当日分钟数据...")
    minute_data = g.data_provider.get_minute_data(
        stock_list=g.stock_list,
        date=current_date,
        period='1m'
    )
    
    if not minute_data or len(minute_data) == 0:
        print(f"警告：日期 {current_date} 没有分钟线数据")
        g.minute_data_cache[current_date] = {}
    else:
        g.minute_data_cache[current_date] = minute_data
        print(f"分钟数据加载成功，股票数: {len(minute_data)}")
    
    old_dates = sorted([d for d in g.minute_data_cache.keys() if d != current_date])
    if len(old_dates) > 3:
        for old_date in old_dates[:-3]:
            del g.minute_data_cache[old_date]
            print(f"清理旧缓存: {old_date}")
    
    current_holdings = g.trade_executor.get_holdings(g.account_id, C)
    current_cash = g.trade_executor.get_cash(g.account_id, C)
    print(f"开盘持仓数: {len(current_holdings)}, 可用资金: {current_cash:.2f}")
    
    open_prices = {}
    for stock_code in g.stock_list:
        if current_date in g.strategy.open_df.index and stock_code in g.strategy.open_df.columns:
            price = g.strategy.open_df.loc[current_date, stock_code]
            if not pd.isna(price) and price > 0:
                open_prices[stock_code] = price
    
    g.day_state = {
        'buy_count': 0,
        'minute_counter': 0,
        'last_signal_count': 0,
        'open_prices': open_prices
    }
    
    g.strategy.init_minute_cache(current_date, g.stock_list)
    
    print(f"交易日 {current_date} 初始化完成\n")


def handlebar(C):
    """
    每分钟交易逻辑（分钟级回测）
    
    Args:
        C: contextinfo对象
    """
    current_bar = C.barpos
    current_timetag = C.get_bar_timetag(current_bar)
    current_date = timetag_to_datetime(current_timetag, "%Y%m%d")
    current_time = timetag_to_datetime(current_timetag, "%H:%M")
    current_timestamp_str = timetag_to_datetime(current_timetag, "%Y%m%d%H%M%S")
    
    if g.day_state.get('minute_counter', 0) == 0:
        print(f"[DEBUG] 首次调用 handlebar:")
        print(f"  current_timetag (毫秒): {current_timetag}")
        print(f"  current_date: {current_date}")
        print(f"  current_time: {current_time}")
        print(f"  current_timestamp_str: {current_timestamp_str}")
        first_stock = list(g.minute_data_cache.get(current_date, {}).keys())[0] if current_date in g.minute_data_cache and g.minute_data_cache[current_date] else None
        if first_stock:
            sample_df = g.minute_data_cache[current_date][first_stock]
            if not sample_df.empty:
                print(f"  缓存数据示例索引: {sample_df.index[:5].tolist()}")
    
    if current_date < g.backtest_start or current_date > g.backtest_end:
        return
    
    if g.current_trading_date is None or current_date != g.current_trading_date:
        start_new_trading_day(current_date, C)
        g.current_trading_date = current_date
    
    g.day_state['minute_counter'] += 1
    
    if current_date not in g.minute_data_cache or not g.minute_data_cache[current_date]:
        return
    
    minute_data = g.minute_data_cache[current_date]
    
    minute_prices = {}
    minute_volumes = {}
    minute_amounts = {}
    
    for stock_code, df in minute_data.items():
        if df.empty:
            continue
        
        if current_timestamp_str in df.index:
            minute_prices[stock_code] = df.loc[current_timestamp_str, 'close']
            minute_volumes[stock_code] = df.loc[current_timestamp_str, 'volume']
            minute_amounts[stock_code] = df.loc[current_timestamp_str, 'amount']
    
    if not minute_prices:
        if g.day_state['minute_counter'] <= 2:
            print(f"[{current_time}] 时间戳 {current_timestamp_str} 无数据（可能非交易时段）")
        return
    
    current_timestamp_dt = datetime.strptime(current_timestamp_str, '%Y%m%d%H%M%S')
    
    g.strategy.update_minute_factors(
        date=current_date,
        minute_timestamp=current_timestamp_dt,
        minute_prices=minute_prices,
        minute_volumes=minute_volumes,
        minute_amounts=minute_amounts
    )
    
    current_holdings = g.trade_executor.get_holdings(g.account_id, C)
    
    if len(current_holdings) > 0 and minute_prices:
        exit_dict = g.strategy.generate_sell_signals(minute_prices, current_date)
        
        if exit_dict:
            print(f"\n[{current_time}] 卖出信号: {len(exit_dict)} 只股票")
            
            print(f"[DEBUG] 卖出前持仓数: {len(current_holdings)}")
            for code, h in list(current_holdings.items())[:5]:
                print(f"[DEBUG]   {code}: 总数量={h.get('volume', 0)}, 可用={h.get('available', 0)}")
            
            for stock_code, reason in exit_dict.items():
                if stock_code in current_holdings:
                    holding = current_holdings[stock_code]
                    total_volume = holding['volume']
                    available_volume = holding.get('available', 0)
                    current_price = minute_prices.get(stock_code, 0)
                    
                    if available_volume <= 0:
                        print(f"[DEBUG] {stock_code} 可用数量为0 (总持仓={total_volume}, 可用={available_volume}), 跳过卖出 (T+1限制)")
                        continue
                    
                    if current_price > 0:
                        sell_price = current_price * (1 - SLIPPAGE_SELL)
                        
                        print(f"  [{current_time}] 卖出 {stock_code}: 价格={sell_price:.2f}, 数量={available_volume}, 原因={reason} (总持仓={total_volume})")
                        
                        order_id = g.trade_executor.sell(
                            g.account_id, stock_code, sell_price, available_volume,
                            'momentum_strategy', f'sell_{reason}', C
                        )
                        print(f"[DEBUG] 卖出下单返回 order_id: {order_id}")
                        
                        holdings_after_sell = g.trade_executor.get_holdings(g.account_id, C)
                        print(f"[DEBUG] 卖出 {stock_code} 后立即查询持仓数: {len(holdings_after_sell)}")
                        print(f"[DEBUG] {stock_code} 是否还在持仓中: {stock_code in holdings_after_sell}")
                        if stock_code in holdings_after_sell:
                            print(f"[DEBUG] {stock_code} 剩余数量: {holdings_after_sell[stock_code].get('volume', 0)}, 可用: {holdings_after_sell[stock_code].get('available', 0)}")
                        
                        g.strategy.on_sell(stock_code)
                    else:
                        print(f"[DEBUG] {stock_code} 无当前价格数据,跳过卖出 (current_price={current_price})")
                else:
                    print(f"[DEBUG] {stock_code} 不在回测引擎持仓中,跳过卖出")
            
            current_holdings = g.trade_executor.get_holdings(g.account_id, C)
            current_cash = g.trade_executor.get_cash(g.account_id, C)
            print(f"  [{current_time}] 卖出后持仓数: {len(current_holdings)}, 可用资金: {current_cash:.2f}")
    
    buy_scores = g.strategy.generate_buy_signals_minute(current_date)
    
    if g.day_state['minute_counter'] <= 3 or len(buy_scores) != g.day_state['last_signal_count']:
        if len(buy_scores) > 0:
            print(f"[{current_time}] 买入信号: {len(buy_scores)} 只股票 (排名前5: {list(buy_scores.head().index)})")
        g.day_state['last_signal_count'] = len(buy_scores)
    
    if len(buy_scores) == 0:
        return
    
    current_holdings = g.trade_executor.get_holdings(g.account_id, C)
    current_cash = g.trade_executor.get_cash(g.account_id, C)
    
    available_slots = g.max_buy_count - len(current_holdings)
    existing_codes = set(current_holdings.keys())
    
    if available_slots <= 0 or current_cash < 10000:
        return
    
    open_prices = g.day_state.get('open_prices', {})
    
    holding_market_value = sum(
        h['volume'] * open_prices.get(s, 0)
        for s, h in current_holdings.items()
    )
    
    for stock_code in buy_scores.index:
        if stock_code in existing_codes:
            continue
        
        if available_slots <= 0 or current_cash < 10000:
            break
        
        market_price = minute_prices.get(stock_code, 0)
        if market_price <= 0:
            continue
        
        buy_price = market_price * (1 + SLIPPAGE_BUY)
        
        total_capital = current_cash + holding_market_value
        
        buy_amount, score = g.strategy.calc_buy_amount(
            stock_code, total_capital, current_date
        )
        
        if buy_amount > current_cash * 0.95:
            buy_amount = current_cash * 0.95
        
        if buy_amount < 10000:
            continue
        
        volume = int(buy_amount / buy_price / 100) * 100
        
        if volume >= 100:
            print(f"  [{current_time}] 买入 {stock_code}: 市价={market_price:.2f}, 挂单价={buy_price:.2f} (+{SLIPPAGE_BUY*100:.1f}%), 数量={volume}, 得分={buy_scores[stock_code]:.1f}")
            
            print(f"[DEBUG] 买入前持仓数: {len(current_holdings)}, {stock_code} 在持仓中: {stock_code in current_holdings}")
            if stock_code in current_holdings:
                print(f"[DEBUG]   已有 {stock_code} 数量: {current_holdings[stock_code].get('volume', 0)}")
            
            order_id = g.trade_executor.buy(
                g.account_id, stock_code, buy_price, volume,
                'momentum_strategy', f'buy_score_{score}', C
            )
            print(f"[DEBUG] 买入下单返回 order_id: {order_id}")
            
            holdings_after_buy = g.trade_executor.get_holdings(g.account_id, C)
            print(f"[DEBUG] 买入 {stock_code} 后立即查询持仓数: {len(holdings_after_buy)}")
            print(f"[DEBUG] {stock_code} 是否在持仓中: {stock_code in holdings_after_buy}")
            if stock_code in holdings_after_buy:
                print(f"[DEBUG] {stock_code} 持仓数量: {holdings_after_buy[stock_code].get('volume', 0)}")
            
            g.strategy.on_buy(stock_code, buy_price, volume, current_date, score, buy_time=current_timestamp_dt)
            
            current_holdings = g.trade_executor.get_holdings(g.account_id, C)
            current_cash = g.trade_executor.get_cash(g.account_id, C)
            available_slots = g.max_buy_count - len(current_holdings)
            existing_codes = set(current_holdings.keys())
            holding_market_value = sum(
                h['volume'] * open_prices.get(s, 0)
                for s, h in current_holdings.items()
            )
            
            g.day_state['buy_count'] += 1



if __name__ == '__main__':
    from xtquant.qmttools import run_strategy_file
    
    param = {
        'stock_code': '000001.SZ',
        'period': '1m',
        'start_time': BACKTEST_CONFIG['start_time'],
        'end_time': BACKTEST_CONFIG['end_time'],
        'trade_mode': 'backtest',
        'quote_mode': 'history',
        'backtest': {
            'slippage_type': 2,
            'slippage': 0.005,
            'max_vol_rate': 0.5,
            'open_commission': 0.0003,
            'close_commission': 0.0003,
            'close_tax': 0.001,
            'min_commission': 5
        }
    }
    
    user_script = sys.argv[0]
    
    print("=" * 60)
    print("启动回测")
    print("=" * 60)
    print(f"脚本路径: {user_script}")
    print(f"回测参数: {param}")
    print("=" * 60)
    
    result = run_strategy_file(user_script, param=param)
    
    if result:
        print("\n" + "=" * 60)
        print("回测结果")
        print("=" * 60)
        
        backtest_index = result.get_backtest_index()
        print("\n回测指标:")
        print(backtest_index)
        
        print("\n分组结果:")
        group_result = result.get_group_result(['order', 'deal', 'position'])
        if 'order' in group_result:
            print(f"\n订单总数: {len(group_result['order'])}")
        if 'deal' in group_result:
            print(f"成交总数: {len(group_result['deal'])}")
        if 'position' in group_result:
            print(f"持仓记录数: {len(group_result['position'])}")
    
    print("\n回测完成")
