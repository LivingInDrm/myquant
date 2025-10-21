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

from xtquant import xtdata

stocks = ['000839.SZ', '002530.SZ', '002115.SZ', '603583.SH']
date = '20250901'

print("=" * 80)
print(f"查询 {date} 09:30 分钟Bar成交量")
print("=" * 80)

for stock in stocks:
    try:
        data = xtdata.get_market_data_ex(
            stock_list=[stock],
            period='1m',
            start_time=date,
            end_time=date
        )
        
        if stock not in data or data[stock].empty:
            print(f"\n{stock}: 无数据")
            continue
        
        df = data[stock]
        
        # 09:30这一分钟
        timestamp_0930 = '20250901093000'
        
        if timestamp_0930 in df.index:
            row = df.loc[timestamp_0930]
            volume = row['volume']
            amount = row['amount']
            close = row['close']
            
            print(f"\n{stock} @ 09:30:00")
            print(f"  收盘价: {close:.2f}")
            print(f"  成交量: {volume:,.0f} 股")
            print(f"  成交额: {amount:,.0f} 元")
            print(f"  25%限制: {volume * 0.25:,.0f} 股")
            print(f"  50%限制: {volume * 0.5:,.0f} 股")
        else:
            print(f"\n{stock}: 时间戳 {timestamp_0930} 不存在")
            print(f"  可用时间戳示例: {df.index[:5].tolist()}")
            
    except Exception as e:
        print(f"\n{stock}: 查询失败 - {e}")

print("\n" + "=" * 80)
