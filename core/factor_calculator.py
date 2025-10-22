# coding: utf-8
import pandas as pd
import numpy as np
from utils.helpers import safe_divide


class FactorCalculator:
    """因子计算层，批量计算技术指标和因子"""
    
    def __init__(self):
        """初始化"""
        self.ma_cache = {}
    
    def calc_ma(self, close_df, periods):
        """
        批量计算移动均线
        
        Args:
            close_df: 收盘价DataFrame (index=date, columns=stock_code)
            periods: 周期列表，如[5, 10, 20, 30, 60, 120]
            
        Returns:
            dict: {period: ma_df}
        """
        ma_dict = {}
        for period in periods:
            ma_dict[period] = close_df.rolling(window=period, min_periods=period).mean()
        return ma_dict
    
    def calc_rolling_max(self, high_df, periods):
        """
        计算N日最高价
        
        Args:
            high_df: 最高价DataFrame
            periods: 周期列表，如[20, 40, 60, 80, 100]
            
        Returns:
            dict: {period: rolling_max_df}
        """
        max_dict = {}
        for period in periods:
            max_dict[period] = high_df.rolling(window=period, min_periods=period).max()
        return max_dict
    
    def calc_volume_ratio(self, volume_df, window=5):
        """
        计算量比（简化版：今日成交量/过去N日平均成交量）
        
        Args:
            volume_df: 成交量DataFrame
            window: 均值窗口，默认5日
            
        Returns:
            pd.DataFrame: 量比DataFrame
        """
        avg_volume = volume_df.rolling(window=window, min_periods=window).mean()
        volume_ratio = safe_divide(volume_df, avg_volume)
        return volume_ratio
    
    def check_consecutive_up_days(self, close_df, days=5):
        """
        检查近N日是否连续上涨
        
        Args:
            close_df: 收盘价DataFrame
            days: 连续天数
            
        Returns:
            pd.DataFrame: 布尔DataFrame
        """
        is_up = (close_df > close_df.shift(1)).astype(int)
        consecutive_up = is_up.rolling(window=days, min_periods=days).sum() == days
        return consecutive_up
    
    def calc_pct_change(self, close_df, days=3):
        """
        计算N日涨跌幅
        
        Args:
            close_df: 收盘价DataFrame
            days: 天数
            
        Returns:
            pd.DataFrame: 涨跌幅DataFrame (百分比)
        """
        return (close_df / close_df.shift(days) - 1) * 100
    
    def check_price_break_ma(self, close_df, ma_dict):
        """
        检查股价是否突破均线
        
        Args:
            close_df: 收盘价DataFrame
            ma_dict: 均线字典 {period: ma_df}
            
        Returns:
            dict: {period: break_df}，布尔DataFrame
        """
        break_dict = {}
        for period, ma_df in ma_dict.items():
            break_dict[period] = close_df > ma_df
        return break_dict
    
    def check_new_high(self, close_df, high_df, periods):
        """
        检查是否创N日新高
        
        Args:
            close_df: 收盘价DataFrame
            high_df: 最高价DataFrame
            periods: 周期列表
            
        Returns:
            dict: {period: new_high_df}，布尔DataFrame
        """
        new_high_dict = {}
        for period in periods:
            rolling_max = high_df.shift(1).rolling(window=period, min_periods=period).max()
            new_high_dict[period] = close_df > rolling_max
        return new_high_dict
    
    def check_ma_arrangement(self, ma_dict, pairs):
        """
        检查均线排列（短期均线是否高于长期均线）
        
        Args:
            ma_dict: 均线字典 {period: ma_df}
            pairs: 均线对列表，如[(5, 10), (10, 20), (20, 30)]
            
        Returns:
            dict: {pair: arrangement_df}，布尔DataFrame
        """
        arrangement_dict = {}
        for short, long in pairs:
            if short in ma_dict and long in ma_dict:
                arrangement_dict[(short, long)] = ma_dict[short] > ma_dict[long]
        return arrangement_dict
    
    def check_volume_expansion(self, volume_df, multiples):
        """
        检查成交量是否是过去10日平均成交量的N倍
        
        Args:
            volume_df: 成交量DataFrame
            multiples: 倍数列表，如[3, 4, 5, 6, 7]
            
        Returns:
            dict: {multiple: expansion_df}，布尔DataFrame
        """
        avg_volume_10 = volume_df.rolling(window=10, min_periods=10).mean()
        expansion_dict = {}
        for multiple in multiples:
            expansion_dict[multiple] = volume_df > (avg_volume_10 * multiple)
        return expansion_dict
    
    def calc_uptrend_score(self, close_df, high_df, volume_df, 
                          ma_dict, max_dict=None):
        """
        计算上涨趋势确定性得分（0-20分）
        
        得分规则：
        1. 股价突破均线（5/10/20/30/60日）：5项，每项1分
        2. 创新高（20/40/60/80/100日）：5项，每项1分
        3. 均线排列：5项，每项1分
        4. 成交量放大（>10日均量3/4/5/6/7倍）：5项，每项1分
        
        Args:
            close_df: 收盘价DataFrame
            high_df: 最高价DataFrame
            volume_df: 成交量DataFrame
            ma_dict: 均线字典
            max_dict: 最高价字典（可选，会自动计算）
            
        Returns:
            pd.DataFrame: 得分DataFrame (0-20分)
        """
        score_df = pd.DataFrame(0, index=close_df.index, columns=close_df.columns)
        
        break_ma_dict = self.check_price_break_ma(close_df, ma_dict)
        for period in [5, 10, 20, 30, 60]:
            if period in break_ma_dict:
                score_df += break_ma_dict[period].astype(int)
        
        if max_dict is None:
            max_dict = self.calc_rolling_max(high_df, [20, 40, 60, 80, 100])
        
        new_high_dict = self.check_new_high(close_df, high_df, [20, 40, 60, 80, 100])
        for period in [20, 40, 60, 80, 100]:
            if period in new_high_dict:
                score_df += new_high_dict[period].astype(int)
        
        ma_pairs = [(10, 5), (20, 10), (30, 20), (60, 30), (120, 60)]
        arrangement_dict = self.check_ma_arrangement(ma_dict, ma_pairs)
        for pair, arrangement_df in arrangement_dict.items():
            score_df += arrangement_df.astype(int)
        
        volume_expansion_dict = self.check_volume_expansion(volume_df, [3, 4, 5, 6, 7])
        for multiple, expansion_df in volume_expansion_dict.items():
            score_df += expansion_df.astype(int)
        
        return score_df
    
    def calc_buy_condition_1(self, close_df, consecutive_days=5, 
                            or_days=3, or_pct_change=6.0):
        """
        计算买入条件1：近5日连续上涨 或 近3日累计涨幅>6%
        
        Args:
            close_df: 收盘价DataFrame
            consecutive_days: 连续上涨天数
            or_days: 或条件的天数
            or_pct_change: 或条件的涨幅阈值
            
        Returns:
            pd.DataFrame: 布尔DataFrame
        """
        cond_consecutive = self.check_consecutive_up_days(close_df, consecutive_days)
        
        pct_change = self.calc_pct_change(close_df, or_days)
        cond_pct = pct_change > or_pct_change
        
        return cond_consecutive | cond_pct
    
    def calc_buy_condition_2_simple(self, volume_df, amount_df, 
                                   volume_ratio_threshold=3, 
                                   amount_threshold=50000000):
        """
        计算买入条件2（简化版，适用于日线回测）
        
        简化逻辑：全天量比>阈值 且 全天成交金额>阈值
        
        Args:
            volume_df: 成交量DataFrame
            amount_df: 成交金额DataFrame
            volume_ratio_threshold: 量比阈值
            amount_threshold: 成交金额阈值
            
        Returns:
            pd.DataFrame: 布尔DataFrame
        """
        volume_ratio = self.calc_volume_ratio(volume_df, window=5)
        
        cond_volume = volume_ratio > volume_ratio_threshold
        cond_amount = amount_df > amount_threshold
        
        return cond_volume & cond_amount
    
    def calc_intraday_volume_ratio(self, cumulative_volume, minutes_since_open, 
                                   daily_avg_vol_per_min):
        """
        计算盘中量比（分钟级）
        
        量比 = (累计成交量 / 累计分钟数) / 过去5日平均每分钟成交量
        
        Args:
            cumulative_volume: 当日截至当前分钟的累计成交量（标量或Series）
            minutes_since_open: 累计开市时间（分钟数，标量）
            daily_avg_vol_per_min: 过去5日平均每分钟成交量（标量或Series）
            
        Returns:
            float或Series: 量比
        """
        if minutes_since_open <= 0:
            return 0
        
        current_avg_vol_per_min = cumulative_volume / minutes_since_open
        volume_ratio = safe_divide(current_avg_vol_per_min, daily_avg_vol_per_min, default=0)
        
        return volume_ratio
    
    def calc_buy_condition_2_intraday(self, volume_ratio, cumulative_amount, 
                                     minutes_since_open):
        """
        计算买入条件2（分钟级）
        
        开盘半小时内：量比>8 且 累计成交额>3000万
        开盘半小时后：量比>3 且 累计成交额>5000万
        
        Args:
            volume_ratio: 量比（标量或Series）
            cumulative_amount: 累计成交额（标量或Series）
            minutes_since_open: 累计开市时间（分钟数）
            
        Returns:
            bool或Series: 是否满足买入条件2
        """
        if minutes_since_open <= 30:
            cond = (volume_ratio > 8) & (cumulative_amount > 30000000)
        else:
            cond = (volume_ratio > 3) & (cumulative_amount > 50000000)
        
        return cond
    
    def calc_minute_score(self, current_price, cumulative_volume, 
                         daily_ma_dict, daily_rolling_max_dict, 
                         past_10d_avg_daily_volume):
        """
        计算分钟级上涨趋势得分（0-20分）
        
        得分规则：
        1. 价格突破MA（5/10/20/30/60日）：5项，每项1分
        2. 创新高（20/40/60/80/100日）：5项，每项1分
        3. 均线排列：5项，每项1分（使用日线MA）
        4. 成交量放大（截止前一分钟累积成交量 > 过去10日平均日成交量的3/4/5/6/7倍）：5项，每项1分
        
        Args:
            current_price: 当前分钟价格（标量或Series）
            cumulative_volume: 截止前一分钟的累积成交量（标量或Series）
            daily_ma_dict: 日线MA字典 {period: value}
            daily_rolling_max_dict: 日线历史最高价字典 {period: value}
            past_10d_avg_daily_volume: 过去10日平均日成交量（标量或Series）
            
        Returns:
            int或Series: 得分（0-20）
        """
        score = 0
        
        for period in [5, 10, 20, 30, 60]:
            if period in daily_ma_dict:
                if isinstance(current_price, (int, float)):
                    score += 1 if current_price > daily_ma_dict[period] else 0
                else:
                    score += (current_price > daily_ma_dict[period]).astype(int)
        
        for period in [20, 40, 60, 80, 100]:
            if period in daily_rolling_max_dict:
                if isinstance(current_price, (int, float)):
                    score += 1 if current_price > daily_rolling_max_dict[period] else 0
                else:
                    score += (current_price > daily_rolling_max_dict[period]).astype(int)
        
        ma_pairs = [(10, 5), (20, 10), (30, 20), (60, 30), (120, 60)]
        for short, long in ma_pairs:
            if short in daily_ma_dict and long in daily_ma_dict:
                if isinstance(daily_ma_dict[short], (int, float)):
                    score += 1 if daily_ma_dict[short] > daily_ma_dict[long] else 0
                else:
                    score += (daily_ma_dict[short] > daily_ma_dict[long]).astype(int)
        
        for multiple in [3, 4, 5, 6, 7]:
            if isinstance(cumulative_volume, (int, float)):
                score += 1 if cumulative_volume > (past_10d_avg_daily_volume * multiple) else 0
            else:
                score += (cumulative_volume > (past_10d_avg_daily_volume * multiple)).astype(int)
        
        return score
