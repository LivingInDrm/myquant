# coding: utf-8
"""
分钟级策略回测示例

演示如何使用升级后的分钟级扫描功能
"""
import pandas as pd
from datetime import datetime
from strategies.momentum_strategy import MomentumStrategy
from core.data_loader import DataLoader
from utils.helpers import calc_minutes_since_open


def minute_backtest_example():
    """分钟级回测示例"""
    
    strategy = MomentumStrategy()
    data_loader = DataLoader()
    
    stock_list = ['600519.SH', '000858.SZ', '600036.SH']
    start_date = '20250901'
    end_date = '20250907'
    
    print("=" * 60)
    print("步骤1: 加载日线数据并计算日频因子")
    print("=" * 60)
    
    daily_data = data_loader.load_daily_data(
        stock_list=stock_list,
        start_date=start_date,
        end_date=end_date
    )
    
    close_df = data_loader.convert_to_matrix_format(daily_data, 'close')
    open_df = data_loader.convert_to_matrix_format(daily_data, 'open')
    high_df = data_loader.convert_to_matrix_format(daily_data, 'high')
    volume_df = data_loader.convert_to_matrix_format(daily_data, 'volume')
    amount_df = data_loader.convert_to_matrix_format(daily_data, 'amount')
    
    strategy.prepare_daily_factors(
        close_df=close_df,
        open_df=open_df,
        high_df=high_df,
        volume_df=volume_df,
        amount_df=amount_df
    )
    
    print("\n" + "=" * 60)
    print("步骤2: 模拟分钟级扫描（以某一天为例）")
    print("=" * 60)
    
    test_date = '20250905'
    
    minute_data = data_loader.load_minute_data(
        stock_list=stock_list,
        date=test_date
    )
    
    if not minute_data:
        print(f"\n警告：日期 {test_date} 没有分钟线数据，可能不是交易日")
        return
    
    strategy.init_minute_cache(test_date, stock_list)
    
    sample_stock = stock_list[0]
    sample_df = minute_data.get(sample_stock, pd.DataFrame())
    
    if sample_df.empty:
        print(f"\n警告：股票 {sample_stock} 没有分钟线数据")
        return
    
    print(f"\n示例股票: {sample_stock}")
    print(f"分钟K线数量: {len(sample_df)}")
    print(f"\n前5条分钟K线数据:")
    print(sample_df.head())
    
    print("\n" + "=" * 60)
    print("步骤3: 按分钟遍历更新因子")
    print("=" * 60)
    
    timestamps = sample_df.index[:10]
    
    for idx, timestamp in enumerate(timestamps):
        minute_prices = {}
        minute_volumes = {}
        minute_amounts = {}
        
        for stock_code in stock_list:
            if stock_code in minute_data:
                stock_df = minute_data[stock_code]
                if timestamp in stock_df.index:
                    minute_prices[stock_code] = stock_df.loc[timestamp, 'close']
                    minute_volumes[stock_code] = stock_df.loc[timestamp, 'volume']
                    minute_amounts[stock_code] = stock_df.loc[timestamp, 'amount']
        
        strategy.update_minute_factors(
            date=test_date,
            minute_timestamp=timestamp,
            minute_prices=minute_prices,
            minute_volumes=minute_volumes,
            minute_amounts=minute_amounts
        )
        
        minutes_since_open = calc_minutes_since_open(timestamp)
        
        if idx < 3 or idx == len(timestamps) - 1:
            print(f"\n时间: {timestamp}, 累计开市: {minutes_since_open}分钟")
            print(f"  价格: {minute_prices}")
            print(f"  成交量: {minute_volumes}")
    
    print("\n" + "=" * 60)
    print("步骤4: 生成买入信号")
    print("=" * 60)
    
    buy_signals = strategy.generate_buy_signals_minute(test_date)
    
    if not buy_signals.empty:
        print(f"\n买入信号数量: {len(buy_signals)}")
        print("\n买入信号详情:")
        for stock_code, score in buy_signals.items():
            print(f"  {stock_code}: 得分={score}")
    else:
        print("\n当日无买入信号")
    
    print("\n" + "=" * 60)
    print("步骤5: 分钟级缓存状态")
    print("=" * 60)
    
    print(f"\n累计成交量缓存 (前3个股票):")
    for i, (stock_code, cache) in enumerate(list(strategy.minute_cache.items())[:3]):
        print(f"  {stock_code}:")
        print(f"    累计成交量: {cache['cum_volume']:,.0f}")
        print(f"    累计成交额: {cache['cum_amount']:,.0f}")
    
    if strategy.minute_scores:
        print(f"\n实时得分:")
        for stock_code, score in strategy.minute_scores.items():
            print(f"  {stock_code}: {score}")
    
    print("\n" + "=" * 60)
    print("完成示例")
    print("=" * 60)


def daily_backtest_compatibility():
    """日线回测兼容性测试（向后兼容）"""
    
    print("\n" + "=" * 60)
    print("日线回测兼容性测试")
    print("=" * 60)
    
    strategy = MomentumStrategy()
    data_loader = DataLoader()
    
    stock_list = ['600519.SH', '000858.SZ']
    start_date = '20250901'
    end_date = '20250907'
    
    daily_data = data_loader.load_daily_data(
        stock_list=stock_list,
        start_date=start_date,
        end_date=end_date
    )
    
    close_df = data_loader.convert_to_matrix_format(daily_data, 'close')
    open_df = data_loader.convert_to_matrix_format(daily_data, 'open')
    high_df = data_loader.convert_to_matrix_format(daily_data, 'high')
    volume_df = data_loader.convert_to_matrix_format(daily_data, 'volume')
    amount_df = data_loader.convert_to_matrix_format(daily_data, 'amount')
    
    strategy.prepare_factors(
        close_df=close_df,
        open_df=open_df,
        high_df=high_df,
        volume_df=volume_df,
        amount_df=amount_df
    )
    
    test_date = close_df.index[-1]
    
    buy_signals = strategy.generate_buy_signals(test_date)
    
    print(f"\n日期: {test_date}")
    print(f"买入信号数量: {len(buy_signals)}")
    if not buy_signals.empty:
        print("\n买入信号:")
        print(buy_signals)
    
    print("\n✓ 日线回测仍然正常工作（向后兼容）")


if __name__ == '__main__':
    print("分钟级策略升级示例\n")
    
    try:
        minute_backtest_example()
    except Exception as e:
        print(f"\n错误: {e}")
        print("请确保:")
        print("1. QMT客户端已启动")
        print("2. 已下载相关股票的历史数据")
        print("3. 日期是有效的交易日")
    
    print("\n" + "=" * 80)
    
    try:
        daily_backtest_compatibility()
    except Exception as e:
        print(f"\n错误: {e}")
