# coding: utf-8
import pandas as pd
import numpy as np


def calculate_limit_prices(close_df, stock_list):
    """
    批量计算涨跌停价
    
    Args:
        close_df: 收盘价 DataFrame (index=日期, columns=股票代码)
        stock_list: 股票列表
        
    Returns:
        tuple: (limit_up_df, limit_down_df)
    """
    prev_close = close_df.shift(1)
    
    limit_ratio = pd.DataFrame(0.10, index=close_df.index, columns=close_df.columns)
    
    columns = close_df.columns
    
    is_gem = pd.Series(
        [c.startswith('300') or c.startswith('301') for c in columns], 
        index=columns
    )
    
    is_kcb = pd.Series(
        [c.startswith('688') for c in columns], 
        index=columns
    )
    
    is_bse = pd.Series(
        [c.startswith('8') or c.startswith('4') for c in columns], 
        index=columns
    )
    
    limit_ratio.loc[:, is_gem] = 0.20
    limit_ratio.loc[:, is_kcb] = 0.20
    limit_ratio.loc[:, is_bse] = 0.30
    
    limit_up = (prev_close * (1 + limit_ratio)).round(2)
    limit_down = (prev_close * (1 - limit_ratio)).round(2)
    
    return limit_up, limit_down
