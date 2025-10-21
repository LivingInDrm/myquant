# coding: utf-8
import pandas as pd
import numpy as np
from xtquant import xtdata
from utils.helpers import get_df_ex, batch_list, print_progress


class DataProvider:
    """数据提供层，封装xtdata数据获取逻辑"""
    
    def __init__(self, batch_size=500):
        """
        初始化
        
        Args:
            batch_size: 批量获取数据时每批的股票数量
        """
        self.batch_size = batch_size
        self.cache = {}
    
    def get_daily_data(self, stock_list, start_time, end_time, 
                      fields=None, dividend_type='front_ratio', fill_data=True):
        """
        批量获取日线数据
        
        Args:
            stock_list: 股票代码列表
            start_time: 开始日期，如'20230101'
            end_time: 结束日期，如'20241231'
            fields: 字段列表，None表示全部字段
            dividend_type: 复权类型 'none', 'front', 'back', 'front_ratio', 'back_ratio'
                          默认'front_ratio'等比前复权，与官方示例保持一致
            fill_data: 是否填充停牌数据
            
        Returns:
            dict: {stock_code: DataFrame} 格式的数据字典
        """
        if fields is None:
            fields = []
        
        cache_key = f"daily_{start_time}_{end_time}_{dividend_type}"
        if cache_key in self.cache:
            print("Using cached data...")
            return self.cache[cache_key]
        
        print(f"Fetching daily data for {len(stock_list)} stocks...")
        
        if len(stock_list) > self.batch_size:
            all_data = {}
            batches = list(batch_list(stock_list, self.batch_size))
            
            for i, batch in enumerate(batches):
                print_progress(i + 1, len(batches), 
                             prefix=f'Batch {i+1}/{len(batches)}:', 
                             suffix='Complete')
                
                batch_data = xtdata.get_market_data_ex(
                    field_list=fields,
                    stock_list=batch,
                    period='1d',
                    start_time=start_time,
                    end_time=end_time,
                    dividend_type=dividend_type,
                    fill_data=fill_data
                )
                all_data.update(batch_data)
            
            data = all_data
        else:
            data = xtdata.get_market_data_ex(
                field_list=fields,
                stock_list=stock_list,
                period='1d',
                start_time=start_time,
                end_time=end_time,
                dividend_type=dividend_type,
                fill_data=fill_data
            )
        
        self.cache[cache_key] = data
        return data
    
    def get_minute_data(self, stock_list, date, period='5m', fields=None, dividend_type='front_ratio'):
        """
        获取分钟线数据
        
        Args:
            stock_list: 股票代码列表
            date: 日期，如'20230101'
            period: 周期 '1m', '5m', '15m', '30m', '60m'
            fields: 字段列表
            dividend_type: 复权类型 'none', 'front', 'back', 'front_ratio', 'back_ratio'
                          默认'front_ratio'等比前复权，与日线数据保持一致
            
        Returns:
            dict: {stock_code: DataFrame}
        """
        if fields is None:
            fields = []
        
        data = xtdata.get_market_data_ex(
            field_list=fields,
            stock_list=stock_list,
            period=period,
            start_time=date,
            end_time=date,
            dividend_type=dividend_type,
            fill_data=True
        )
        
        return data
    
    def get_tick_data(self, stock_list, date, fields=None):
        """
        获取tick数据
        
        Args:
            stock_list: 股票代码列表
            date: 日期
            fields: 字段列表
            
        Returns:
            dict: {stock_code: DataFrame}
        """
        if fields is None:
            fields = []
        
        data = xtdata.get_market_data_ex(
            field_list=fields,
            stock_list=stock_list,
            period='tick',
            start_time=date,
            end_time=date
        )
        
        return data
    
    def get_instrument_info(self, stock_list):
        """
        批量获取合约基础信息
        
        Args:
            stock_list: 股票代码列表
            
        Returns:
            dict: {stock_code: info_dict}
        """
        print(f"Fetching instrument info for {len(stock_list)} stocks...")
        
        info_dict = {}
        for i, stock in enumerate(stock_list):
            if (i + 1) % 100 == 0:
                print_progress(i + 1, len(stock_list), 
                             prefix='Progress:', suffix='')
            
            try:
                info = xtdata.get_instrument_detail(stock)
                info_dict[stock] = info
            except Exception as e:
                print(f"Error fetching info for {stock}: {e}")
                info_dict[stock] = None
        
        return info_dict
    
    def get_stock_list_in_sector(self, sector_name='沪深A股'):
        """
        获取板块成分股
        
        Args:
            sector_name: 板块名称
            
        Returns:
            list: 股票代码列表
        """
        return xtdata.get_stock_list_in_sector(sector_name)
    
    def get_trading_dates(self, start_date, end_date, market='SH'):
        """
        获取交易日列表
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            market: 市场代码
            
        Returns:
            list: 交易日列表
        """
        dates = xtdata.get_trading_dates(market, start_date, end_date)
        return [str(d) for d in dates]
    
    def download_history_data(self, stock_list, period='1d', 
                            start_date='', end_date=''):
        """
        下载历史数据到本地
        
        Args:
            stock_list: 股票代码列表
            period: 周期
            start_date: 开始日期
            end_date: 结束日期
        """
        print(f"Downloading {period} data for {len(stock_list)} stocks...")
        
        for i, stock in enumerate(stock_list):
            if (i + 1) % 50 == 0:
                print_progress(i + 1, len(stock_list), 
                             prefix='Downloading:', suffix='')
            
            try:
                xtdata.download_history_data(stock, period, start_date, end_date)
            except Exception as e:
                print(f"Error downloading {stock}: {e}")
    
    def convert_to_dataframes(self, data, fields):
        """
        将get_market_data_ex返回的数据转换为字段DataFrame字典
        
        Args:
            data: get_market_data_ex返回的dict
            fields: 字段列表
            
        Returns:
            dict: {field: DataFrame}
        """
        dfs = {}
        for field in fields:
            dfs[field] = get_df_ex(data, field)
        return dfs
    
    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()
        print("Cache cleared")
