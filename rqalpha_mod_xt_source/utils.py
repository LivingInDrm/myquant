#coding: utf-8

import numpy as np
import pandas as pd
from datetime import datetime


CODE_SUFFIX_MAP = {
    'XSHE': 'SZ',
    'XSHG': 'SH',
    'XBSE': 'BJ',
}

REVERSE_CODE_SUFFIX_MAP = {v: k for k, v in CODE_SUFFIX_MAP.items()}


def rqalpha_to_xt_code(order_book_id):
    """
    RQAlpha代码格式转换为QMT代码格式
    
    Args:
        order_book_id: RQAlpha格式代码，如 '000001.XSHE', '600519.XSHG'
    
    Returns:
        QMT格式代码，如 '000001.SZ', '600519.SH'
    
    Examples:
        >>> rqalpha_to_xt_code('000001.XSHE')
        '000001.SZ'
        >>> rqalpha_to_xt_code('600519.XSHG')
        '600519.SH'
        >>> rqalpha_to_xt_code('688001.XSHG')
        '688001.SH'
    """
    if '.' not in order_book_id:
        raise ValueError(f"Invalid order_book_id format: {order_book_id}")
    
    symbol, suffix = order_book_id.rsplit('.', 1)
    
    if suffix not in CODE_SUFFIX_MAP:
        raise ValueError(f"Unknown exchange suffix: {suffix}, order_book_id: {order_book_id}")
    
    xt_suffix = CODE_SUFFIX_MAP[suffix]
    return f"{symbol}.{xt_suffix}"


def xt_to_rqalpha_code(xt_code):
    """
    QMT代码格式转换为RQAlpha代码格式
    
    Args:
        xt_code: QMT格式代码，如 '000001.SZ', '600519.SH'
    
    Returns:
        RQAlpha格式代码，如 '000001.XSHE', '600519.XSHG'
    
    Examples:
        >>> xt_to_rqalpha_code('000001.SZ')
        '000001.XSHE'
        >>> xt_to_rqalpha_code('600519.SH')
        '600519.XSHG'
    """
    if '.' not in xt_code:
        raise ValueError(f"Invalid xt_code format: {xt_code}")
    
    symbol, suffix = xt_code.rsplit('.', 1)
    
    if suffix not in REVERSE_CODE_SUFFIX_MAP:
        raise ValueError(f"Unknown exchange suffix: {suffix}, xt_code: {xt_code}")
    
    rqalpha_suffix = REVERSE_CODE_SUFFIX_MAP[suffix]
    return f"{symbol}.{rqalpha_suffix}"


def convert_xt_datetime_to_int(dt_obj):
    """
    将datetime对象或字符串转换为RQAlpha使用的uint64整数格式
    
    Args:
        dt_obj: datetime对象、pandas Timestamp对象或日期时间字符串
    
    Returns:
        uint64整数，格式为YYYYMMDDHHmmss
    
    Examples:
        >>> from datetime import datetime
        >>> convert_xt_datetime_to_int(datetime(2024, 1, 1, 9, 30, 0))
        20240101093000
        >>> convert_xt_datetime_to_int('2024-01-01 09:30:00')
        20240101093000
    """
    if isinstance(dt_obj, pd.Timestamp):
        dt_obj = dt_obj.to_pydatetime()
    elif isinstance(dt_obj, str):
        try:
            dt_obj = pd.to_datetime(dt_obj)
            if isinstance(dt_obj, pd.Timestamp):
                dt_obj = dt_obj.to_pydatetime()
        except Exception:
            dt_clean = dt_obj.replace('-', '').replace(':', '').replace(' ', '')
            return np.uint64(int(dt_clean[:14]))
    
    dt_str = dt_obj.strftime('%Y%m%d%H%M%S')
    return np.uint64(int(dt_str))


def xt_df_to_bar_array(df, stock_code=None):
    """
    将xtquant返回的DataFrame转换为RQAlpha使用的numpy structured array
    
    Args:
        df: xtquant返回的DataFrame，index为DatetimeIndex，
            columns包含: open, high, low, close, volume, amount等
        stock_code: 股票代码（可选，用于调试）
    
    Returns:
        numpy structured array，dtype包含:
        - datetime: uint64, YYYYMMDDHHmmss格式
        - open: float64
        - high: float64
        - low: float64
        - close: float64
        - volume: float64
        - total_turnover: float64 (从amount字段映射)
    """
    if df is None or df.empty:
        return None
    
    n = len(df)
    
    dtype = np.dtype([
        ('datetime', np.uint64),
        ('open', np.float64),
        ('high', np.float64),
        ('low', np.float64),
        ('close', np.float64),
        ('volume', np.float64),
        ('total_turnover', np.float64),
    ])
    
    result = np.zeros(n, dtype=dtype)
    
    result['datetime'] = [convert_xt_datetime_to_int(dt) for dt in df.index]
    
    if 'open' in df.columns:
        result['open'] = df['open'].values
    if 'high' in df.columns:
        result['high'] = df['high'].values
    if 'low' in df.columns:
        result['low'] = df['low'].values
    if 'close' in df.columns:
        result['close'] = df['close'].values
    if 'volume' in df.columns:
        result['volume'] = df['volume'].values
    if 'amount' in df.columns:
        result['total_turnover'] = df['amount'].values
    
    return result


def xt_df_to_field_array(df, fields):
    """
    将xtquant返回的DataFrame转换为指定字段的numpy array
    用于history_bars返回特定字段
    
    Args:
        df: xtquant返回的DataFrame
        fields: 字段名或字段列表，如 'close' 或 ['open', 'close', 'volume']
    
    Returns:
        numpy structured array 或 numpy array，根据请求的fields类型决定
    """
    if df is None or df.empty:
        return None
    
    if isinstance(fields, str):
        single_field = True
        fields = [fields]
    else:
        single_field = False
    
    n = len(df)
    
    if 'datetime' in fields:
        dtype_list = []
        values_dict = {}
        
        for field in fields:
            if field == 'datetime':
                dtype_list.append(('datetime', np.uint64))
                values_dict['datetime'] = np.array([convert_xt_datetime_to_int(dt) for dt in df.index], dtype=np.uint64)
            elif field == 'total_turnover':
                dtype_list.append(('total_turnover', np.float64))
                if 'amount' in df.columns:
                    values_dict['total_turnover'] = df['amount'].values.astype(np.float64)
                else:
                    values_dict['total_turnover'] = np.zeros(n, dtype=np.float64)
            elif field in df.columns:
                dtype_list.append((field, np.float64))
                values_dict[field] = df[field].values.astype(np.float64)
            else:
                dtype_list.append((field, np.float64))
                values_dict[field] = np.zeros(n, dtype=np.float64)
        
        result = np.zeros(n, dtype=np.dtype(dtype_list))
        for field in values_dict:
            result[field] = values_dict[field]
        
        return result
    else:
        xt_fields = []
        for field in fields:
            if field == 'total_turnover':
                xt_fields.append('amount')
            else:
                xt_fields.append(field)
        
        available_fields = [f for f in xt_fields if f in df.columns]
        
        if len(available_fields) == 0:
            return None
        
        if single_field:
            return df[available_fields[0]].values
        else:
            return df[available_fields].values
