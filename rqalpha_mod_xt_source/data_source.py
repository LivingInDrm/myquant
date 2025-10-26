#coding: utf-8

from datetime import datetime, date
from typing import Optional, Union
import numpy as np

from rqalpha.data.base_data_source import BaseDataSource
from rqalpha.model.instrument import Instrument
from rqalpha.utils.datetime_func import convert_date_to_int
from rqalpha.utils.logger import system_log

from .utils import (
    rqalpha_to_xt_code,
    xt_df_to_bar_array,
    xt_df_to_field_array,
)


class XTDataSource(BaseDataSource):
    """
    混合数据源：分钟数据从QMT获取，其他数据使用RQAlpha默认数据源
    """
    
    MINUTE_FREQUENCIES = ['1m', '5m', '15m', '30m', '60m']
    
    def __init__(self, path, custom_future_info=None):
        """
        初始化数据源
        
        Args:
            path: RQAlpha bundle数据路径
            custom_future_info: 自定义期货信息（传递给BaseDataSource）
        """
        if custom_future_info is None:
            custom_future_info = {}
        
        super(XTDataSource, self).__init__(path, custom_future_info)
        
        try:
            from xtquant import xtdata
            self._xtdata = xtdata
            self._minute_cache = {}
            system_log.info("[XTDataSource] 成功导入xtquant.xtdata模块")
        except ImportError as e:
            system_log.error(f"[XTDataSource] 无法导入xtquant模块: {e}")
            raise
    
    def _is_minute_frequency(self, frequency):
        """判断是否为分钟级频率"""
        return frequency in self.MINUTE_FREQUENCIES
    
    def _get_xt_frequency_period(self, frequency):
        """
        RQAlpha频率转换为xtquant的period参数
        
        Args:
            frequency: RQAlpha频率，如 '1m', '5m'
        
        Returns:
            xtquant period，如 '1m', '5m'
        """
        return frequency
    
    def _get_xt_dividend_type(self, adjust_type):
        """
        RQAlpha复权类型转换为xtquant的dividend_type参数
        
        Args:
            adjust_type: RQAlpha复权类型 'pre'/'post'/'none'
        
        Returns:
            xtquant dividend_type: 'front_ratio'/'back_ratio'/'none'
        """
        mapping = {
            'pre': 'front_ratio',
            'post': 'back_ratio',
            'none': 'none',
        }
        return mapping.get(adjust_type, 'front_ratio')
    
    def _format_date_str(self, dt):
        """
        将datetime、date对象或日期字符串/整数转换为xtquant需要的日期字符串
        
        Args:
            dt: datetime、date对象、字符串或整数
        
        Returns:
            str: 格式化的日期字符串 'YYYYMMDD'
        """
        if isinstance(dt, datetime):
            return dt.strftime('%Y%m%d')
        elif isinstance(dt, date):
            return dt.strftime('%Y%m%d')
        elif isinstance(dt, str):
            dt_clean = dt.replace('-', '').replace('/', '').replace(' ', '')
            if len(dt_clean) >= 8:
                return dt_clean[:8]
            return dt_clean
        elif isinstance(dt, int):
            dt_str = str(dt)
            if len(dt_str) >= 8:
                return dt_str[:8]
            return dt_str
        else:
            return str(dt)
    
    def get_bar(self, instrument, dt, frequency):
        """
        获取指定时间的bar数据
        
        分钟频率从QMT获取，其他频率使用父类方法
        """
        if not self._is_minute_frequency(frequency):
            return super(XTDataSource, self).get_bar(instrument, dt, frequency)
        
        try:
            xt_code = rqalpha_to_xt_code(instrument.order_book_id)
        except ValueError as e:
            system_log.warning(f"[XTDataSource] 代码转换失败: {e}")
            return None
        
        period = self._get_xt_frequency_period(frequency)
        date_str = self._format_date_str(dt)
        
        cache_key = f"{xt_code}_{period}_{date_str}_bar"
        if cache_key in self._minute_cache:
            return self._minute_cache[cache_key]
        
        try:
            field_list = ['open', 'high', 'low', 'close', 'volume', 'amount']
            
            data = self._xtdata.get_market_data_ex(
                field_list=field_list,
                stock_list=[xt_code],
                period=period,
                start_time=date_str,
                end_time=date_str,
                dividend_type='front_ratio',
                fill_data=True
            )
            
            if not data or xt_code not in data:
                return None
            
            df = data[xt_code]
            
            if df is None or df.empty:
                return None
            
            bar_array = xt_df_to_bar_array(df, xt_code)
            
            if bar_array is None or len(bar_array) == 0:
                return None
            
            result = bar_array[0]
            self._minute_cache[cache_key] = result
            return result
            
        except Exception as e:
            system_log.error(f"[XTDataSource] 获取{xt_code}的{frequency}数据失败: {e}")
            return None
    
    def history_bars(self, instrument, bar_count, frequency, fields, dt,
                     skip_suspended=True, include_now=False,
                     adjust_type='pre', adjust_orig=None):
        """
        获取历史bar数据
        
        分钟频率从QMT获取，其他频率使用父类方法
        """
        if not self._is_minute_frequency(frequency):
            return super(XTDataSource, self).history_bars(
                instrument, bar_count, frequency, fields, dt,
                skip_suspended, include_now, adjust_type, adjust_orig
            )
        
        try:
            xt_code = rqalpha_to_xt_code(instrument.order_book_id)
        except ValueError as e:
            system_log.warning(f"[XTDataSource] 代码转换失败: {e}")
            return None
        
        period = self._get_xt_frequency_period(frequency)
        dividend_type = self._get_xt_dividend_type(adjust_type)
        date_str = self._format_date_str(dt)
        
        cache_key = f"{xt_code}_{period}_{date_str}_{bar_count}_{dividend_type}"
        if cache_key in self._minute_cache:
            cached_result = self._minute_cache[cache_key]
            if fields is None:
                return cached_result
            else:
                return cached_result if fields is None else cached_result[fields] if hasattr(cached_result, '__getitem__') else xt_df_to_field_array(self._minute_cache.get(f"{cache_key}_df"), fields)
        
        try:
            if fields is None:
                field_list = []
            elif isinstance(fields, str):
                field_list = [fields if fields != 'total_turnover' else 'amount']
            else:
                field_list = [f if f != 'total_turnover' else 'amount' for f in fields]
            
            data = self._xtdata.get_market_data_ex(
                field_list=field_list,
                stock_list=[xt_code],
                period=period,
                start_time='',
                end_time=date_str,
                count=bar_count,
                dividend_type=dividend_type,
                fill_data=not skip_suspended
            )
            
            if not data or xt_code not in data:
                return None
            
            df = data[xt_code]
            
            if df is None or df.empty:
                return None
            
            self._minute_cache[f"{cache_key}_df"] = df
            
            if fields is None:
                result = xt_df_to_bar_array(df, xt_code)
                self._minute_cache[cache_key] = result
                return result
            else:
                result = xt_df_to_field_array(df, fields)
                return result
                
        except Exception as e:
            system_log.error(f"[XTDataSource] 获取{xt_code}的{frequency}历史数据失败: {e}")
            return None
    
    def available_data_range(self, frequency):
        """
        获取可用数据范围
        
        分钟频率根据QMT数据确定，其他频率使用父类方法
        """
        from datetime import date, timedelta
        
        if self._is_minute_frequency(frequency):
            return date(2020, 1, 1), date.today() - timedelta(days=1)
        
        try:
            result = super(XTDataSource, self).available_data_range(frequency)
            if result is None:
                system_log.warning(f"[XTDataSource] 父类返回None，使用默认范围")
                return date(2015, 1, 1), date.today() - timedelta(days=1)
            return result
        except Exception as e:
            system_log.warning(f"[XTDataSource] 获取数据范围失败: {e}，使用默认范围")
            return date(2015, 1, 1), date.today() - timedelta(days=1)
