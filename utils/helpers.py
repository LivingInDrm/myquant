# coding: utf-8
import pandas as pd
import numpy as np
from datetime import datetime
from xtquant import xtdata


def timetag_to_datetime(timetag, fmt="%Y%m%d"):
    """
    将时间戳转换为日期字符串
    
    Args:
        timetag: 时间戳（毫秒）
        fmt: 格式化字符串
        
    Returns:
        str: 格式化后的日期字符串
    """
    if isinstance(timetag, (int, float)):
        dt = datetime.fromtimestamp(timetag / 1000)
        return dt.strftime(fmt)
    return timetag


def datetime_to_timetag(date_str):
    """
    将日期字符串转换为时间戳
    
    Args:
        date_str: 日期字符串，如'20230101'或'2023-01-01'
        
    Returns:
        int: 时间戳（毫秒）
    """
    if isinstance(date_str, str):
        date_str = date_str.replace('-', '').replace(':', '').replace(' ', '')
        if len(date_str) == 8:
            dt = datetime.strptime(date_str, "%Y%m%d")
        elif len(date_str) == 14:
            dt = datetime.strptime(date_str, "%Y%m%d%H%M%S")
        else:
            raise ValueError(f"Unsupported date format: {date_str}")
        return int(dt.timestamp() * 1000)
    return date_str


def get_df_ex(data: dict, field: str) -> pd.DataFrame:
    """
    从get_market_data_ex返回的dict中提取指定字段，转换为标准DataFrame
    
    Args:
        data: get_market_data_ex返回的dict
        field: 字段名 ['time', 'open', 'high', 'low', 'close', 'volume', 'amount', ...]
        
    Returns:
        pd.DataFrame: 以时间为index，股票代码为columns的DataFrame
    """
    if not data:
        return pd.DataFrame()
    
    _index = data[list(data.keys())[0]].index.tolist()
    _columns = list(data.keys())
    df = pd.DataFrame(index=_index, columns=_columns)
    
    for stock_code in _columns:
        if field in data[stock_code].columns:
            df[stock_code] = data[stock_code][field].values
        else:
            df[stock_code] = np.nan
    
    return df


def rank_filter(df: pd.DataFrame, N: int, axis=1, ascending=False, 
                method="min", na_option="keep") -> pd.DataFrame:
    """
    对DataFrame按行或列排名，返回是否在前N名的布尔DataFrame
    
    Args:
        df: 输入DataFrame
        N: 判断是否是前N名
        axis: 0-按列排序，1-按行排序（默认）
        ascending: True-升序，False-降序（默认）
        method: 排名方法 ('average', 'min', 'max', 'first', 'dense')
        na_option: 'keep'-保留NaN不参与排名, 'top'-NaN排在最前, 'bottom'-NaN排在最后
        
    Returns:
        pd.DataFrame: 布尔值DataFrame，True表示在前N名
    """
    _df = df.copy()
    _df = _df.rank(axis=axis, ascending=ascending, method=method, na_option=na_option)
    return _df <= N


def filter_opendate(stock_list: list, df: pd.DataFrame, n: int, 
                   data_source='xtdata') -> pd.DataFrame:
    """
    判断股票上市天数是否大于N天
    
    Args:
        stock_list: 股票代码列表
        df: 以时间为index，股票代码为columns的DataFrame（用于对齐）
        n: 上市天数阈值
        data_source: 'xtdata' 或 'contextinfo'
        
    Returns:
        pd.DataFrame: 布尔值DataFrame，True表示上市天数>=n
    """
    result_df = pd.DataFrame(index=df.index, columns=df.columns, dtype=bool)
    result_df[:] = False
    
    if data_source == 'xtdata':
        stock_opendate = {
            stock: xtdata.get_instrument_detail(stock).get("OpenDate", "19700101")
            for stock in stock_list
        }
    else:
        raise ValueError("Unsupported data_source")
    
    for stock, opendate_str in stock_opendate.items():
        if not opendate_str or opendate_str == "19700101":
            continue
        
        try:
            open_date = pd.to_datetime(opendate_str)
            
            for date in df.index:
                current_date = pd.to_datetime(date)
                days_since_open = (current_date - open_date).days
                
                if days_since_open >= n:
                    result_df.at[date, stock] = True
        except (ValueError, TypeError):
            continue
    
    return result_df


def is_st_stock(stock_code: str, his_st_dict: dict, date: str) -> bool:
    """
    判断某日股票是否是ST或*ST
    
    Args:
        stock_code: 股票代码
        his_st_dict: 历史ST数据字典 {stock_code: {'ST': [[start, end], ...], '*ST': [...]}}
        date: 日期字符串，如'20230101'
        
    Returns:
        bool: True-是ST，False-不是ST
    """
    st_dict = his_st_dict.get(stock_code, {})
    if not st_dict:
        return False
    
    st_periods = st_dict.get('ST', []) + st_dict.get('*ST', [])
    for start, end in st_periods:
        if start <= date <= end:
            return True
    
    return False


def filter_st_stocks(stock_list: list, date: str, his_st_dict: dict) -> list:
    """
    过滤掉ST股票
    
    Args:
        stock_list: 股票代码列表
        date: 日期字符串
        his_st_dict: 历史ST数据字典
        
    Returns:
        list: 非ST股票列表
    """
    return [s for s in stock_list if not is_st_stock(s, his_st_dict, date)]


def filter_suspended_stocks(stock_df: pd.DataFrame, date: str) -> pd.Series:
    """
    过滤停牌股票
    
    Args:
        stock_df: DataFrame，包含suspendFlag列
        date: 日期
        
    Returns:
        pd.Series: 布尔Series，True表示未停牌
    """
    if date in stock_df.index and 'suspendFlag' in stock_df.columns:
        return stock_df.loc[date, 'suspendFlag'] == 0
    return pd.Series(True, index=stock_df.columns)


def batch_list(data: list, batch_size: int):
    """
    将列表分批
    
    Args:
        data: 输入列表
        batch_size: 每批大小
        
    Yields:
        list: 分批后的子列表
    """
    for i in range(0, len(data), batch_size):
        yield data[i:i + batch_size]


def safe_divide(a, b, default=np.nan):
    """
    安全除法，避免除零错误
    
    Args:
        a: 被除数
        b: 除数
        default: 除零时的默认值
        
    Returns:
        除法结果或默认值
    """
    if isinstance(a, pd.Series) or isinstance(a, pd.DataFrame):
        return a.divide(b).replace([np.inf, -np.inf], default)
    else:
        return a / b if b != 0 else default


def print_progress(current, total, prefix='Progress:', suffix='', decimals=1, bar_length=50):
    """
    打印进度条
    
    Args:
        current: 当前进度
        total: 总数
        prefix: 前缀
        suffix: 后缀
        decimals: 小数位数
        bar_length: 进度条长度
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (current / float(total)))
    filled_length = int(bar_length * current // total)
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end='')
    if current == total:
        print()


def calc_minutes_since_open(timestamp):
    """
    计算累计开市时间（从9:30开始计数）
    
    上午9:30-11:30共121分钟，下午13:00-15:00共121分钟
    
    Args:
        timestamp: datetime对象、字符串或整数（如 20250901093000）
        
    Returns:
        int: 累计分钟数（1-242），如果不在交易时间返回0
    """
    if isinstance(timestamp, (str, int)):
        if isinstance(timestamp, int):
            timestamp = str(timestamp)
        timestamp = pd.to_datetime(timestamp, format='%Y%m%d%H%M%S')
    
    hour = timestamp.hour
    minute = timestamp.minute
    
    if hour == 9 and minute >= 30:
        return minute - 29
    elif hour == 10:
        return 31 + minute
    elif hour == 11 and minute <= 30:
        return 91 + minute
    elif hour == 13:
        return 121 + minute
    elif hour == 14:
        return 181 + minute
    elif hour == 15 and minute == 0:
        return 241
    else:
        return 0


def calc_cumulative_volume(minute_df, current_idx):
    """
    计算当日累计成交量
    
    Args:
        minute_df: 分钟线DataFrame，包含volume列
        current_idx: 当前时间索引
        
    Returns:
        float: 截至当前分钟的累计成交量
    """
    if current_idx not in minute_df.index:
        return 0
    
    current_date = pd.to_datetime(current_idx).date()
    
    today_mask = pd.to_datetime(minute_df.index).date == current_date
    today_data = minute_df[today_mask]
    
    current_loc = today_data.index.get_loc(current_idx)
    
    cumulative_vol = today_data.iloc[:current_loc+1]['volume'].sum()
    
    return cumulative_vol


def calc_daily_avg_volume_per_minute(daily_volume, window=10):
    """
    计算过去N日平均每分钟成交量
    
    Args:
        daily_volume: 日线成交量Series或DataFrame
        window: 窗口期（天数）
        
    Returns:
        Series或DataFrame: 每个日期对应的过去N日平均每分钟成交量
    """
    total_minutes_per_day = 240
    
    avg_volume = daily_volume.rolling(window=window, min_periods=window).sum()
    
    avg_volume_per_minute = avg_volume / (window * total_minutes_per_day)
    
    return avg_volume_per_minute
