from xtquant import xtdata
import pandas as pd

# 目标股票
stocks = ['000839.SZ', '002530.SZ', '002115.SZ', '688235.SH', '603583.SH']

# 查询日期（根据你的回测日期调整）
date_str = '20250901'  # 2025年
start_time = '20250901093000'
end_time = '20250901093100'

print(f"查询时段: {start_time} - {end_time}\n")
print("=" * 80)

for stock_code in stocks:
    try:
        # 获取1分钟K线数据
        data = xtdata.get_market_data_ex(
            field_list=['volume', 'open', 'high', 'low', 'close', 'amount'],
            stock_list=[stock_code],
            period='1m',
            start_time=start_time,
            end_time=end_time
        )
        
        if stock_code in data and not data[stock_code].empty:
            df = data[stock_code]
            print(f"\n{stock_code}:")
            # 尝试多种时间格式
            try:
                time_val = df.index[0]
                if isinstance(time_val, (int, float)) and time_val > 1e12:
                    time_str = pd.to_datetime(int(time_val), unit='ms').strftime('%Y-%m-%d %H:%M:%S')
                else:
                    time_str = str(time_val)
                print(f"  时间: {time_str}")
            except:
                print(f"  时间: {df.index[0]}")
            print(f"  成交量: {df['volume'].iloc[0]:,.0f} 股")
            print(f"  成交额: {df['amount'].iloc[0]:,.2f} 元")
            print(f"  开盘: {df['open'].iloc[0]:.2f}")
            print(f"  最高: {df['high'].iloc[0]:.2f}")
            print(f"  最低: {df['low'].iloc[0]:.2f}")
            print(f"  收盘: {df['close'].iloc[0]:.2f}")
            
            # 计算 max_vol_rate=0.5 时的理论最大成交量
            max_buy = int(df['volume'].iloc[0] * 0.5)
            print(f"  理论最大买入量(50%): {max_buy:,} 股")
        else:
            print(f"\n{stock_code}: 无数据")
            
    except Exception as e:
        print(f"\n{stock_code}: 查询失败 - {e}")

print("\n" + "=" * 80)
print("\n对比实际成交:")
print("  000839.SZ: 申报=7900, 成交=2500")
print("  002530.SZ: 申报=2000, 成交=100")
print("  002115.SZ: 申报=2700, 成交=200")
print("  603583.SH: 申报=500,  成交=0")
