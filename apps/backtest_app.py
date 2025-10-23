# coding: utf-8
import sys
import io
import os
from datetime import datetime as dt_now

# 添加项目根目录到 Python 路径，以便导入 xtquant 等模块
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 创建UTF-8编码的日志文件（单例模式，避免重复创建）
if not hasattr(sys, '_backtest_log_initialized'):
    log_file_path = f"backtest_log_{dt_now.now().strftime('%Y%m%d_%H%M%S')}.txt"
    log_file = open(log_file_path, 'w', encoding='utf-8', buffering=1)
    sys._backtest_log_initialized = True
    sys._backtest_log_file = log_file
else:
    log_file = sys._backtest_log_file

# 重定向输出到日志文件（仅第一次初始化时）
if not hasattr(sys, '_backtest_stdout_replaced'):
    sys.stdout = log_file
    sys.stderr = log_file
    sys._backtest_stdout_replaced = True
    
    print(f"[INFO] Log file created: {log_file_path}")
    print(f"[INFO] All output will be saved to UTF-8 encoded log file")

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from xtquant import xtdata

from data.data_provider import DataProvider
from core.trade_executor import TradeExecutor
from strategies.momentum.strategy import MomentumStrategy
from utils.helpers import get_df_ex, filter_opendate, timetag_to_datetime
from config.strategy_config import STOCK_POOL
from config.backtest_config import load_backtest_config

BACKTEST_CONFIG = load_backtest_config()


def save_backtest_results(backtest_index, group_result, start_time, end_time):
    """
    保存回测结果到文件
    
    Args:
        backtest_index: 回测指标（Series或DataFrame）
        group_result: 分组结果字典，包含order、deal、position等
        start_time: 回测开始时间（格式：'YYYYMMDD'或'YYYY-MM-DD'）
        end_time: 回测结束时间（格式：'YYYYMMDD'或'YYYY-MM-DD'）
    """
    result_dir = os.path.join(project_root, 'result')
    os.makedirs(result_dir, exist_ok=True)
    
    timestamp = dt_now.now().strftime('%Y%m%d_%H%M%S')
    start_clean = start_time.replace('-', '')
    end_clean = end_time.replace('-', '')
    
    run_dir = os.path.join(result_dir, f'backtest_{start_clean}_{end_clean}_{timestamp}')
    os.makedirs(run_dir, exist_ok=True)
    
    if backtest_index is not None:
        if isinstance(backtest_index, pd.DataFrame):
            if not backtest_index.empty and 'time' in backtest_index.columns:
                backtest_index = backtest_index[
                    (backtest_index['time'] >= start_clean) & 
                    (backtest_index['time'] <= end_clean)
                ]
        
        index_file = os.path.join(run_dir, 'backtest_index.csv')
        if isinstance(backtest_index, pd.Series):
            backtest_index.to_csv(index_file, encoding='utf-8-sig')
        else:
            backtest_index.to_csv(index_file, index=False, encoding='utf-8-sig')
        print(f"[OK] 回测指标已保存: {index_file}")
    
    if group_result:
        for key, df in group_result.items():
            if df is not None and not df.empty:
                group_file = os.path.join(run_dir, f'{key}.csv')
                df.to_csv(group_file, index=False, encoding='utf-8-sig')
                print(f"[OK] {key} 数据已保存: {group_file}")
    
    print(f"[OK] 所有结果已保存到目录: {run_dir}")


class G:
    """全局变量容器"""
    pass


g = G()


def init(C):
    """
    初始化函数，在回测启动前调用一次
    
    Args:
        C: contextinfo对象
    """
    
    g.stock_pool_name = STOCK_POOL
    g.account_id = 'test'
    
    g.data_provider = DataProvider(batch_size=500)
    g.trade_executor = TradeExecutor(mode='backtest', strategy_name='momentum_strategy')
    g.strategy = MomentumStrategy(account=g.account_id, strategy_name='momentum_strategy')
    
    g.stock_list = C.get_stock_list_in_sector(g.stock_pool_name)
    
    g.minute_data_cache = {}
    g.current_trading_date = None
    g.day_state = {
        'buy_count': 0,
        'minute_counter': 0,
        'last_signal_count': 0,
        'open_prices': {}
    }
    


def after_init(C):
    """
    初始化后处理，预先计算所有因子
    
    Args:
        C: contextinfo对象
    """  
    start_time = BACKTEST_CONFIG['start_time'].replace('-', '')
    end_time = BACKTEST_CONFIG['end_time'].replace('-', '')
    
    warmup_days = 365
    data_start_time = pd.to_datetime(start_time) - pd.Timedelta(days=warmup_days)
    data_start_time_str = data_start_time.strftime('%Y%m%d')
    
    g.backtest_start = start_time
    g.backtest_end = end_time
    
    data = g.data_provider.get_daily_data(
        stock_list=g.stock_list,
        start_time=data_start_time_str,
        end_time=end_time,
        dividend_type='front_ratio',
        fill_data=True
    )
    
    if not data:
        print("错误：无法获取历史数据")
        return
    

    close_df = get_df_ex(data, 'close')
    open_df = get_df_ex(data, 'open')
    high_df = get_df_ex(data, 'high')
    volume_df = get_df_ex(data, 'volume')
    amount_df = get_df_ex(data, 'amount')
    

    listing_filter_df = filter_opendate(g.stock_list, close_df, 120, 'xtdata')
    
    g.strategy.prepare_daily_factors(
        close_df, open_df, high_df, volume_df, amount_df,
        stock_list=g.stock_list,
        listing_filter_df=listing_filter_df
    )
    



def start_new_trading_day(current_date, C):
    """
    交易日切换处理
    
    Args:
        current_date: 当前交易日（字符串格式，如'20240115'）
        C: contextinfo对象
    """
    
    minute_data = g.data_provider.get_minute_data(
        stock_list=g.stock_list,
        date=current_date,
        period='1m',
        dividend_type='front_ratio'
    )
    
    if not minute_data or len(minute_data) == 0:
        print(f"警告：日期 {current_date} 没有分钟线数据")
        g.minute_data_cache[current_date] = pd.DataFrame()
    else:
        minute_data_multi = pd.concat(
            minute_data,
            names=['stock_code', 'timestamp']
        )
        g.minute_data_cache[current_date] = minute_data_multi
        print(f"分钟数据加载成功，股票数: {len(minute_data)}, 转换为MultiIndex DataFrame")
    
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
    
    if current_date < g.backtest_start or current_date > g.backtest_end:
        return
    
    if g.current_trading_date is None or current_date != g.current_trading_date:
        start_new_trading_day(current_date, C)
        g.current_trading_date = current_date
    
    g.day_state['minute_counter'] += 1
    
    g.strategy.sync_metadata_with_holdings()
    
    # 获取分钟K线数据
    if current_date not in g.minute_data_cache:
        return
    
    minute_data_multi = g.minute_data_cache[current_date]
    
    if minute_data_multi.empty:
        return
    
    current_timestamp_dt = datetime.strptime(current_timestamp_str, '%Y%m%d%H%M%S')
    
    # 计算上一分钟的时间戳（用于因子计算，避免前视偏差）
    prev_timestamp_dt = current_timestamp_dt - timedelta(minutes=1)
    prev_timestamp_str = prev_timestamp_dt.strftime('%Y%m%d%H%M%S')
    
    # 获取上一分钟K线数据（用于因子计算）
    # 如果上一分钟没有数据（9:30开盘或13:00午盘），会在KeyError处理中return
    try:
        prev_minute_data = minute_data_multi.xs(
            prev_timestamp_str,
            level='timestamp'
        ).to_dict('index')
    except KeyError:
        # 上一分钟没有数据：9:30(上一分钟9:29)或13:00(上一分钟12:59)
        return
    
    if not prev_minute_data:
        return
    
    # 获取当前分钟K线数据（用于买入价格）
    try:
        current_minute_data = minute_data_multi.xs(
            current_timestamp_str,
            level='timestamp'
        ).to_dict('index')
    except KeyError:
        current_minute_data = {}
    
    # 更新分钟级因子（使用上一分钟的完整数据）
    g.strategy.update_minute_factors(
        date=current_date,
        minute_timestamp=prev_timestamp_dt,
        minute_data=prev_minute_data
    )
    

    minute_prices = {stock: data['close'] for stock, data in current_minute_data.items()}
    minute_opens = {stock: data['open'] for stock, data in current_minute_data.items()}
    minute_highs = {stock: data['high'] for stock, data in current_minute_data.items()}
    minute_lows = {stock: data['low'] for stock, data in current_minute_data.items()}
    minute_volumes = {stock: data['volume'] for stock, data in current_minute_data.items()}
    minute_amounts = {stock: data['amount'] for stock, data in current_minute_data.items()}
    
    current_holdings = g.trade_executor.get_holdings(g.account_id, C)
    
    if len(current_holdings) > 0 and minute_prices:
        exit_dict = g.strategy.generate_sell_signals(minute_prices, current_date, holdings_dict=current_holdings)
        
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
                        sell_price = current_price
                        
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
    
    # 时间过滤：10:00之前不交易
    current_hour = int(current_time.split(':')[0])
    current_minute = int(current_time.split(':')[1])
    current_time_value = current_hour * 60 + current_minute
    if current_time_value < 10 * 60:  # 10:00 = 600分钟
        if g.day_state['minute_counter'] <= 3:
            print(f"[{current_time}] 10:00之前不交易，跳过买入")
        return
    
    current_holdings = g.trade_executor.get_holdings(g.account_id, C)
    current_cash = g.trade_executor.get_cash(g.account_id, C)
    
    existing_codes = set(current_holdings.keys())
    
    if current_cash < 10000:
        return
    
    open_prices = g.day_state.get('open_prices', {})
    
    holding_market_value = sum(
        h['volume'] * open_prices.get(s, 0)
        for s, h in current_holdings.items()
    )
    
    for stock_code in buy_scores.index:
        if stock_code in existing_codes:
            continue
        
        if current_cash < 10000:
            break
        
        # 使用当前分钟开盘价作为买入价格（实盘中可立即成交）
        open_price = minute_opens.get(stock_code, 0)
        if open_price <= 0:
            continue
        
        buy_price = open_price
        
        total_capital = current_cash + holding_market_value
        
        buy_amount, score = g.strategy.calc_buy_amount(
            stock_code, total_capital
        )
        
        if buy_amount > current_cash * 0.95:
            buy_amount = current_cash * 0.95
        
        if buy_amount < 10000:
            continue
        
        volume = int(buy_amount / buy_price / 100) * 100
        
        if volume >= 100:
            print(f"  [{current_time}] 买入 {stock_code}: 开盘价={buy_price:.2f}, 数量={volume}, 得分={buy_scores[stock_code]:.1f}")
            
            print(f"[DEBUG] 买入前持仓数: {len(current_holdings)}, {stock_code} 在持仓中: {stock_code in current_holdings}")
            if stock_code in current_holdings:
                print(f"[DEBUG]   已有 {stock_code} 数量: {current_holdings[stock_code].get('volume', 0)}")
            
            print("=" * 60)
            print(f"[买入前调试信息] {stock_code}")
            print("-" * 60)
            print(f"[股票信息]")
            print(f"  代码: {stock_code}")
            print(f"  买入价(开盘): {buy_price:.2f}")
            print(f"  数量: {volume}")
            print(f"  评分: {score:.2f}")
            print(f"  信号评分: {buy_scores[stock_code]:.2f}")
            
            print(f"[当前分钟K线] {current_time}")
            minute_open = minute_opens.get(stock_code, 0)
            minute_high = minute_highs.get(stock_code, 0)
            minute_low = minute_lows.get(stock_code, 0)
            minute_close = minute_prices.get(stock_code, 0)
            minute_vol = minute_volumes.get(stock_code, 0)
            minute_amt = minute_amounts.get(stock_code, 0)
            print(f"  开盘: {minute_open:.2f}")
            print(f"  最高: {minute_high:.2f}")
            print(f"  最低: {minute_low:.2f}")
            print(f"  收盘: {minute_close:.2f}")
            print(f"  成交量: {minute_vol:,.0f}")
            print(f"  成交额: {minute_amt:,.2f}")
            if minute_vol > 0:
                print(f"  振幅: {((minute_high - minute_low) / minute_open * 100):.2f}%")
            
            print(f"[账户信息]")
            print(f"  可用资金: {current_cash:.2f}")
            print(f"  总资产: {total_capital:.2f}")
            print(f"  持仓市值: {holding_market_value:.2f}")
            print(f"  资金使用率: {(holding_market_value/total_capital*100 if total_capital > 0 else 0):.2f}%")
            
            print(f"[持仓元数据]")
            all_metadata = g.strategy.metadata_mgr.get_all_metadata()
            if all_metadata:
                for code, meta in all_metadata.items():
                    print(f"  {code}: 买入日期={meta.get('buy_date')}, 评分={meta.get('score')}, 目标收益={meta.get('target_profit', 0)*100:.2f}%")
            else:
                print("  当前无持仓元数据")
            
            print(f"[当前持仓]")
            if current_holdings:
                for code, pos in current_holdings.items():
                    print(f"  {code}: 数量={pos.get('volume', 0)}, 成本={pos.get('cost', 0):.2f}, 可用={pos.get('available', 0)}")
            else:
                print("  当前无持仓")
            print("=" * 60)
            
            order_id = g.trade_executor.buy(
                g.account_id, stock_code, buy_price, volume,
                'momentum_strategy', f'buy_score_{score}', C
            )
            
            g.strategy.on_buy(stock_code, current_date, score, buy_time=current_timestamp_dt)
            
            current_holdings = g.trade_executor.get_holdings(g.account_id, C)
            current_cash = g.trade_executor.get_cash(g.account_id, C)
            existing_codes = set(current_holdings.keys())
            holding_market_value = sum(
                h['volume'] * open_prices.get(s, 0)
                for s, h in current_holdings.items()
            )
            
            g.day_state['buy_count'] += 1



if __name__ == '__main__':
    from xtquant.qmttools import run_strategy_file
    from config.backtest_config import build_backtest_param
    
    param = build_backtest_param(BACKTEST_CONFIG)
    
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
        
        print("\n" + "=" * 60)
        print("保存回测结果")
        print("=" * 60)
        save_backtest_results(
            backtest_index,
            group_result,
            BACKTEST_CONFIG['start_time'],
            BACKTEST_CONFIG['end_time']
        )
    
    print("\n回测完成")
