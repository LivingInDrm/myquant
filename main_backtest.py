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
from xtquant import xtdata

from core.data_provider import DataProvider
from core.trade_executor import TradeExecutor
from strategies.momentum_strategy import MomentumStrategy
from utils.helpers import get_df_ex, filter_opendate, timetag_to_datetime
from config.strategy_config import BACKTEST_CONFIG, MAX_POSITIONS


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
    
    g.stock_list = g.data_provider.get_stock_list_in_sector(g.stock_pool_name)
    print(f"股票池: {g.stock_pool_name}, 股票数量: {len(g.stock_list)}")
    
    g.account_id = 'test'
    g.money = 1000000
    
    g.max_buy_count = MAX_POSITIONS
    
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
    
    g.strategy.prepare_factors(
        close_df, open_df, high_df, volume_df, amount_df,
        stock_list=g.stock_list,
        listing_filter_df=listing_filter_df
    )
    
    print("=" * 60)
    print("数据预处理完成，开始回测")
    print("=" * 60)


def handlebar(C):
    """
    每日交易逻辑
    
    Args:
        C: contextinfo对象
    """
    current_bar = C.barpos
    current_timetag = C.get_bar_timetag(current_bar)
    current_date = timetag_to_datetime(current_timetag, "%Y%m%d")
    
    if current_date < g.backtest_start or current_date > g.backtest_end:
        return
    
    print(f"\n{'=' * 60}")
    print(f"交易日: {current_date}")
    print(f"{'=' * 60}")
    
    print(f"[DEBUG] 开始获取持仓和资金信息...")
    print(f"[DEBUG] account_id={g.account_id}, C类型={type(C)}")
    
    current_holdings = g.trade_executor.get_holdings(g.account_id, C)
    print(f"[DEBUG] 持仓信息: {current_holdings}")
    
    current_cash = g.trade_executor.get_cash(g.account_id, C)
    print(f"[DEBUG] 获取到的资金: {current_cash}")
    
    print(f"当前持仓数: {len(current_holdings)}, 可用资金: {current_cash:.2f}")
    
    current_prices = {}
    for stock_code in g.stock_list:
        if current_date in g.strategy.open_df.index and stock_code in g.strategy.open_df.columns:
            price = g.strategy.open_df.loc[current_date, stock_code]
            if not pd.isna(price) and price > 0:
                current_prices[stock_code] = price
    
    exit_dict = g.strategy.generate_sell_signals(current_prices, current_date)
    
    if exit_dict:
        print(f"\n卖出信号: {len(exit_dict)} 只股票")
        for stock_code, reason in exit_dict.items():
            if stock_code in current_holdings:
                holding = current_holdings[stock_code]
                volume = holding['volume']
                price = current_prices.get(stock_code, 0)
                
                if price > 0:
                    print(f"  卖出 {stock_code}: 价格={price:.2f}, 数量={volume}, 原因={reason}")
                    
                    g.trade_executor.sell(
                        g.account_id, stock_code, price, volume,
                        'momentum_strategy', f'sell_{reason}', C
                    )
                    
                    g.strategy.on_sell(stock_code)
    
    print(f"[DEBUG] 卖出后重新获取持仓和资金...")
    current_holdings = g.trade_executor.get_holdings(g.account_id, C)
    current_cash = g.trade_executor.get_cash(g.account_id, C)
    print(f"[DEBUG] 卖出后资金: {current_cash}")
    
    available_slots = g.max_buy_count - len(current_holdings)
    
    if available_slots > 0 and current_cash > 10000:
        print(f"\n生成买入信号...")
        buy_scores = g.strategy.generate_buy_signals(current_date)
        print(f"买入信号数量: {len(buy_scores)}")
        
        if len(buy_scores) > 0:
            print(f"前5个买入信号: {buy_scores.head()}")
            buy_list = g.strategy.filter_buy_list(buy_scores, current_date, available_slots)
            
            existing_codes = set(current_holdings.keys())
            buy_list = [s for s in buy_list if s not in existing_codes]
            
            if buy_list:
                print(f"买入信号: {len(buy_list)} 只股票")
                
                for stock_code in buy_list:
                    price = current_prices.get(stock_code, 0)
                    
                    if price <= 0:
                        continue
                    
                    total_capital = current_cash + sum(
                        h['volume'] * current_prices.get(s, 0) 
                        for s, h in current_holdings.items()
                    )
                    
                    buy_amount, score = g.strategy.calc_buy_amount(
                        stock_code, total_capital, current_date
                    )
                    
                    if buy_amount > current_cash * 0.95:
                        buy_amount = current_cash * 0.95
                    
                    if buy_amount < 10000:
                        continue
                    
                    volume = int(buy_amount / price / 100) * 100
                    
                    if volume >= 100:
                        print(f"  买入 {stock_code}: 价格={price:.2f}, 数量={volume}, 得分={score}")
                        
                        g.trade_executor.buy(
                            g.account_id, stock_code, price, volume,
                            'momentum_strategy', f'buy_score_{score}', C
                        )
                        
                        g.strategy.on_buy(stock_code, price, volume, current_date, score)
                        
                        current_cash -= volume * price
                        
                        if current_cash < 10000:
                            break


if __name__ == '__main__':
    from xtquant.qmttools import run_strategy_file
    
    param = {
        'stock_code': '000001.SZ',
        'period': '1d',
        'start_time': BACKTEST_CONFIG['start_time'],
        'end_time': BACKTEST_CONFIG['end_time'],
        'trade_mode': 'backtest',
        'quote_mode': 'history'
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
        for key, value in backtest_index.items():
            print(f"  {key}: {value}")
        
        print("\n分组结果:")
        group_result = result.get_group_result()
        print(group_result)
    
    print("\n回测完成")
