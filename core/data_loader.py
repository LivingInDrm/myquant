# coding: utf-8
import pandas as pd
import numpy as np
from xtquant import xtdata
from utils.helpers import get_df_ex


class DataLoader:
    """数据加载器，封装 xtdata 调用"""
    
    def __init__(self):
        """初始化"""
        self.daily_cache = {}
        self.minute_cache = {}
    
    def load_daily_data(self, stock_list, start_date, end_date, 
                       field_list=None, dividend_type='front', fill_data=True):
        """
        加载日线数据
        
        Args:
            stock_list: 股票代码列表
            start_date: 开始日期，格式 '20240101'
            end_date: 结束日期，格式 '20241018'
            field_list: 字段列表，默认 ['open', 'high', 'low', 'close', 'volume', 'amount']
            dividend_type: 复权类型，'none'不复权, 'front'前复权, 'back'后复权
            fill_data: 是否填充停牌日数据
            
        Returns:
            dict: {股票代码: DataFrame}
        """
        if field_list is None:
            field_list = ['open', 'high', 'low', 'close', 'volume', 'amount']
        
        cache_key = f"{start_date}_{end_date}_{dividend_type}"
        if cache_key in self.daily_cache:
            print(f"Loading daily data from cache: {cache_key}")
            return self.daily_cache[cache_key]
        
        print(f"Loading daily data: {len(stock_list)} stocks, {start_date} to {end_date}")
        
        data = xtdata.get_market_data_ex(
            stock_list=stock_list,
            period='1d',
            start_time=start_date,
            end_time=end_date,
            dividend_type=dividend_type,
            fill_data=fill_data,
            field_list=field_list
        )
        
        self.daily_cache[cache_key] = data
        
        print(f"Daily data loaded: {len(data)} stocks")
        return data
    
    def load_minute_data(self, stock_list, date, 
                        field_list=None, dividend_type='front'):
        """
        加载指定日期的分钟线数据
        
        Args:
            stock_list: 股票代码列表
            date: 日期，格式 '20241018'
            field_list: 字段列表，默认 ['open', 'high', 'low', 'close', 'volume', 'amount']
            dividend_type: 复权类型
            
        Returns:
            dict: {股票代码: DataFrame}
        """
        if field_list is None:
            field_list = ['open', 'high', 'low', 'close', 'volume', 'amount']
        
        cache_key = f"{date}_{dividend_type}"
        if cache_key in self.minute_cache:
            print(f"Loading minute data from cache: {cache_key}")
            return self.minute_cache[cache_key]
        
        print(f"Loading minute data: {len(stock_list)} stocks, date {date}")
        
        data = xtdata.get_market_data_ex(
            stock_list=stock_list,
            period='1m',
            start_time=date,
            end_time=date,
            dividend_type=dividend_type,
            fill_data=False,
            field_list=field_list
        )
        
        self.minute_cache[cache_key] = data
        
        print(f"Minute data loaded: {len(data)} stocks")
        return data
    
    def convert_to_matrix_format(self, data_dict, field='close'):
        """
        将 get_market_data_ex 返回的 dict 转换为矩阵格式（股票×时间）
        
        Args:
            data_dict: get_market_data_ex 返回的字典 {股票代码: DataFrame}
            field: 要提取的字段名
            
        Returns:
            pd.DataFrame: 以时间为 index，股票代码为 columns 的 DataFrame
        """
        return get_df_ex(data_dict, field)
    
    def clear_cache(self):
        """清空缓存"""
        self.daily_cache.clear()
        self.minute_cache.clear()
        print("Cache cleared")
    
    def get_cache_info(self):
        """
        获取缓存信息
        
        Returns:
            dict: 缓存统计信息
        """
        return {
            'daily_cache_size': len(self.daily_cache),
            'minute_cache_size': len(self.minute_cache),
            'daily_cache_keys': list(self.daily_cache.keys()),
            'minute_cache_keys': list(self.minute_cache.keys())
        }
