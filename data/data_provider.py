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
