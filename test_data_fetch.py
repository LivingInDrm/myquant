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
import pandas as pd

print("开始测试数据获取...")

target_stocks = [
    '000839.SZ',
    '002115.SZ',
    '002210.SZ',
    '002530.SZ',
    '002564.SZ'
]

print(f"目标股票: {target_stocks}")
print("获取分钟数据...")

try:
    data = xtdata.get_market_data_ex(
        stock_list=target_stocks,
        period='1m',
        start_time='20250901',
        end_time='20250901',
        dividend_type='front_ratio',
        fill_data=True
    )
    
    if data:
        print(f"[OK] 获取到 {len(data)} 只股票的数据")
        for stock, df in data.items():
            print(f"  {stock}: {len(df)} 条数据")
            if len(df) > 0:
                print(f"    时间范围: {df.index[0]} ~ {df.index[-1]}")
                print(f"    示例数据: open={df['open'].iloc[0]:.2f}, close={df['close'].iloc[0]:.2f}")
    else:
        print("[FAIL] 未获取到数据")
        
except Exception as e:
    print(f"[ERROR] 获取数据失败: {e}")
    import traceback
    traceback.print_exc()

print("\n测试完成")
