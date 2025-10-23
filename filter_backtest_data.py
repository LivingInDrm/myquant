# coding: utf-8
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
import os

# 输入文件路径
input_file = r'd:\program\myquant\results\backtest_20251023_105235\backtest_index.csv'

# 输出文件路径（同目录下）
output_dir = os.path.dirname(input_file)
output_file = os.path.join(output_dir, 'backtest_index_20250901_20251001.csv')

print(f"[INFO] 读取文件: {input_file}")

# 读取 CSV（第一列是无名索引列）
df = pd.read_csv(input_file, encoding='utf-8-sig')

print(f"[INFO] 原始数据行数: {len(df)}")
print(f"[INFO] 列名: {list(df.columns)}")

# 时间列名是"时间"
time_column = '时间'

if time_column not in df.columns:
    print(f"[FAIL] 未找到时间列，可用列: {list(df.columns)}")
    sys.exit(1)

# 转换时间为字符串格式（确保是字符串）
df[time_column] = df[time_column].astype(str)

# 筛选日期区间：2025-09-01 ~ 2025-10-01
# 时间格式是 YYYYMMDDHHMMSS
start_date = '20250901'
end_date = '20251001'

# 筛选条件：时间 >= 20250901000000 且 <= 20251001235959
filtered_df = df[
    (df[time_column] >= start_date + '000000') & 
    (df[time_column] <= end_date + '235959')
]

print(f"[INFO] 筛选后数据行数: {len(filtered_df)}")

if len(filtered_df) > 0:
    print(f"[INFO] 时间范围: {filtered_df[time_column].min()} ~ {filtered_df[time_column].max()}")
    
    # 保存筛选后的数据
    filtered_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"[OK] 已保存筛选结果: {output_file}")
else:
    print(f"[WARN] 筛选结果为空，未找到 {start_date} ~ {end_date} 区间的数据")
    print(f"[INFO] 原始数据时间范围: {df[time_column].min()} ~ {df[time_column].max()}")
