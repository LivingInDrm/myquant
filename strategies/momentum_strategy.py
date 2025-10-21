# coding: utf-8
import pandas as pd
import numpy as np
from datetime import datetime
from core.factor_calculator import FactorCalculator
from core.position_metadata import PositionMetadata
from core.position_data_wrapper import PositionDataWrapper
from utils.helpers import (
    filter_st_stocks, calc_minutes_since_open, 
    calc_daily_avg_volume_per_minute
)
from config.strategy_config import (
    BUY_CONDITION_1, BUY_CONDITION_2, MIN_LISTING_DAYS, MAX_POSITIONS,
    DAILY_AVG_VOLUME_WINDOW_5D, DAILY_AVG_VOLUME_WINDOW_10D,
    STOP_LOSS, MAX_HOLD_DAYS
)


class MomentumStrategy:
    """短期强势股策略"""
    
    def __init__(self, account=None, strategy_name=''):
        self.factor_calc = FactorCalculator()
        self.metadata_mgr = PositionMetadata()
        self.position_wrapper = PositionDataWrapper(account, strategy_name) if account else None
        
        self.close_df = None
        self.open_df = None
        self.high_df = None
        self.volume_df = None
        self.amount_df = None
        
        self.ma_dict = None
        self.rolling_max_dict = None
        self.score_df = None
        self.buy_cond1_df = None
        self.buy_cond2_df = None
        
        self.daily_avg_vol_per_min_5d = None
        self.daily_avg_vol_per_min_10d = None
        
        self.minute_cache = {}
        self.minute_scores = {}
        self.minute_buy_cond2 = {}
        
        self.his_st_dict = {}
        self.listing_filter_df = None
    
    def prepare_daily_factors(self, close_df, open_df, high_df, volume_df, amount_df, 
                             stock_list=None, listing_filter_df=None):
        """
        预先计算所有日频因子（每日盘前调用一次）
        
        Args:
            close_df: 收盘价DataFrame
            open_df: 开盘价DataFrame
            high_df: 最高价DataFrame
            volume_df: 成交量DataFrame
            amount_df: 成交金额DataFrame
            stock_list: 股票列表（用于上市日期过滤）
            listing_filter_df: 上市日期过滤DataFrame（可选）
        """
        print("Preparing daily factors...")
        
        self.close_df = close_df.shift(1)
        self.open_df = open_df
        self.high_df = high_df.shift(1)
        self.volume_df = volume_df.shift(1)
        self.amount_df = amount_df.shift(1)
        
        print("Calculating moving averages...")
        self.ma_dict = self.factor_calc.calc_ma(close_df, [5, 10, 20, 30, 60, 120])
        for period in self.ma_dict:
            self.ma_dict[period] = self.ma_dict[period].shift(1)
        
        print("Calculating rolling max...")
        self.rolling_max_dict = self.factor_calc.calc_rolling_max(
            high_df, [20, 40, 60, 80, 100]
        )
        for period in self.rolling_max_dict:
            self.rolling_max_dict[period] = self.rolling_max_dict[period].shift(1)
        
        print("Calculating uptrend scores (daily)...")
        self.score_df = self.factor_calc.calc_uptrend_score(
            self.close_df, self.high_df, self.volume_df, self.ma_dict
        )
        
        print("Calculating buy condition 1...")
        self.buy_cond1_df = self.factor_calc.calc_buy_condition_1(
            close_df,
            consecutive_days=BUY_CONDITION_1['consecutive_up_days'],
            or_days=BUY_CONDITION_1['or_days'],
            or_pct_change=BUY_CONDITION_1['or_pct_change']
        ).shift(1)
        
        print("Calculating buy condition 2 (daily)...")
        self.buy_cond2_df = self.factor_calc.calc_buy_condition_2_simple(
            volume_df, amount_df,
            volume_ratio_threshold=BUY_CONDITION_2['late_volume_ratio'],
            amount_threshold=BUY_CONDITION_2['late_amount']
        ).shift(1)
        
        print("Calculating daily average volume per minute (5d & 10d)...")
        self.daily_avg_vol_per_min_5d = calc_daily_avg_volume_per_minute(
            volume_df, window=DAILY_AVG_VOLUME_WINDOW_5D
        ).shift(1)
        
        self.daily_avg_vol_per_min_10d = calc_daily_avg_volume_per_minute(
            volume_df, window=DAILY_AVG_VOLUME_WINDOW_10D
        ).shift(1)
        
        if listing_filter_df is not None:
            self.listing_filter_df = listing_filter_df
        
        print("Daily factors prepared successfully")
    
    def init_minute_cache(self, date, stock_list):
        """
        初始化分钟级缓存（每日开盘时调用）
        
        Args:
            date: 日期
            stock_list: 股票代码列表
        """
        self.minute_cache = {}
        self.minute_scores = {}
        self.minute_buy_cond2 = {}
        
        for stock_code in stock_list:
            self.minute_cache[stock_code] = {
                'cum_volume': 0,
                'cum_amount': 0
            }
    
    def update_minute_factors(self, date, minute_timestamp, minute_prices, 
                             minute_volumes, minute_amounts):
        """
        更新分钟级因子（每分钟调用）
        
        Args:
            date: 日期（字符串或datetime对象）
            minute_timestamp: 分钟时间戳（datetime）
            minute_prices: 价格字典 {stock_code: price}
            minute_volumes: 成交量字典 {stock_code: volume}
            minute_amounts: 成交额字典 {stock_code: amount}
        """
        if isinstance(date, str):
            date = pd.to_datetime(date)
        
        date_normalized = date.normalize()
        
        matched_date = None
        for idx_date in self.daily_avg_vol_per_min_5d.index:
            if pd.to_datetime(idx_date).normalize() == date_normalized:
                matched_date = idx_date
                break
        
        if matched_date is None:
            return
        
        date = matched_date
        
        minutes_since_open = calc_minutes_since_open(minute_timestamp)
        if minutes_since_open <= 0:
            return
        
        for stock_code in minute_prices.keys():
            if stock_code not in self.minute_cache:
                continue
            
            price = minute_prices.get(stock_code, np.nan)
            volume = minute_volumes.get(stock_code, 0)
            amount = minute_amounts.get(stock_code, 0)
            
            if pd.isna(price) or price <= 0:
                continue
            
            self.minute_cache[stock_code]['cum_volume'] += volume
            self.minute_cache[stock_code]['cum_amount'] += amount
            
            cum_volume = self.minute_cache[stock_code]['cum_volume']
            cum_amount = self.minute_cache[stock_code]['cum_amount']
            
            try:
                if stock_code not in self.daily_avg_vol_per_min_5d.columns:
                    continue
                avg_vol_per_min_5d = self.daily_avg_vol_per_min_5d.loc[date, stock_code]
                if pd.isna(avg_vol_per_min_5d) or avg_vol_per_min_5d <= 0:
                    continue
            except (KeyError, IndexError):
                continue
            
            volume_ratio = self.factor_calc.calc_intraday_volume_ratio(
                cum_volume, minutes_since_open, avg_vol_per_min_5d
            )
            
            buy_cond2 = self.factor_calc.calc_buy_condition_2_intraday(
                volume_ratio, cum_amount, minutes_since_open
            )
            self.minute_buy_cond2[stock_code] = buy_cond2
            
            daily_ma = {}
            try:
                for period in [5, 10, 20, 30, 60, 120]:
                    if period in self.ma_dict and date in self.ma_dict[period].index:
                        if stock_code in self.ma_dict[period].columns:
                            daily_ma[period] = self.ma_dict[period].loc[date, stock_code]
            except (KeyError, IndexError):
                pass
            
            daily_rolling_max = {}
            try:
                for period in [20, 40, 60, 80, 100]:
                    if period in self.rolling_max_dict and date in self.rolling_max_dict[period].index:
                        if stock_code in self.rolling_max_dict[period].columns:
                            daily_rolling_max[period] = self.rolling_max_dict[period].loc[date, stock_code]
            except (KeyError, IndexError):
                pass
            
            if not daily_ma or not daily_rolling_max:
                continue
            
            try:
                if stock_code not in self.daily_avg_vol_per_min_10d.columns:
                    continue
                avg_vol_per_min_10d = self.daily_avg_vol_per_min_10d.loc[date, stock_code]
                if pd.isna(avg_vol_per_min_10d) or avg_vol_per_min_10d <= 0:
                    avg_vol_per_min_10d = 1
            except (KeyError, IndexError):
                avg_vol_per_min_10d = 1
            
            score = self.factor_calc.calc_minute_score(
                price, volume, daily_ma, daily_rolling_max, avg_vol_per_min_10d
            )
            self.minute_scores[stock_code] = score
    
    def generate_buy_signals_minute(self, date):
        """
        生成买入信号（分钟级）
        
        Args:
            date: 日期（字符串或datetime对象）
            
        Returns:
            pd.Series: 股票得分Series (得分>=8的股票)
        """
        if isinstance(date, str):
            date = pd.to_datetime(date)
        
        date_normalized = date.normalize()
        
        matched_date = None
        for idx_date in self.buy_cond1_df.index:
            if pd.to_datetime(idx_date).normalize() == date_normalized:
                matched_date = idx_date
                break
        
        if matched_date is None:
            return pd.Series(dtype=float)
        
        cond1 = self.buy_cond1_df.loc[matched_date]
        
        result_scores = pd.Series(dtype=float)
        
        for stock_code in self.minute_scores.keys():
            if stock_code not in cond1.index:
                continue
            
            if not cond1[stock_code]:
                continue
            
            cond2 = self.minute_buy_cond2.get(stock_code, False)
            if not cond2:
                continue
            
            score = self.minute_scores[stock_code]
            if score >= 8:
                if self.listing_filter_df is not None and matched_date in self.listing_filter_df.index:
                    if stock_code in self.listing_filter_df.columns:
                        if not self.listing_filter_df.loc[matched_date, stock_code]:
                            continue
                
                result_scores[stock_code] = score
        
        return result_scores.sort_values(ascending=False)
    
    def prepare_factors(self, close_df, open_df, high_df, volume_df, amount_df, 
                       stock_list=None, listing_filter_df=None):
        """
        向后兼容方法（调用 prepare_daily_factors）
        
        Args:
            close_df: 收盘价DataFrame
            open_df: 开盘价DataFrame
            high_df: 最高价DataFrame
            volume_df: 成交量DataFrame
            amount_df: 成交金额DataFrame
            stock_list: 股票列表（用于上市日期过滤）
            listing_filter_df: 上市日期过滤DataFrame（可选）
        """
        return self.prepare_daily_factors(close_df, open_df, high_df, volume_df, 
                                          amount_df, stock_list, listing_filter_df)
    
    def generate_buy_signals(self, date):
        """
        生成买入信号
        
        Args:
            date: 日期
            
        Returns:
            pd.Series: 股票得分Series (得分>=8的股票)
        """
        if date not in self.score_df.index:
            print(f"[策略] 日期{date}不在数据范围内")
            return pd.Series(dtype=float)
        
        cond1 = self.buy_cond1_df.loc[date]
        cond2 = self.buy_cond2_df.loc[date]
        scores = self.score_df.loc[date]
        
        print(f"[策略] cond1满足: {cond1.sum()} | cond2满足: {cond2.sum()} | scores>=8: {(scores>=8).sum()}")
        
        buy_signal = cond1 & cond2
        print(f"[策略] cond1 & cond2: {buy_signal.sum()}")
        
        valid_stocks = buy_signal & (scores >= 8)
        print(f"[策略] (cond1 & cond2) & scores>=8: {valid_stocks.sum()}")
        
        if valid_stocks.sum() > 0:
            candidate_stocks = scores[valid_stocks].sort_values(ascending=False)
            print(f"[策略] 候选股票(应用上市过滤前):")
            for stock_code, score in candidate_stocks.head(10).items():
                print(f"  {stock_code}: 得分={score:.1f}")
        
        if self.listing_filter_df is not None and date in self.listing_filter_df.index:
            listing_filter = self.listing_filter_df.loc[date]
            
            filtered_out = valid_stocks & (~listing_filter)
            if filtered_out.sum() > 0:
                print(f"[策略] 被上市过滤拦截的股票({filtered_out.sum()}只):")
                filtered_scores = scores[filtered_out].sort_values(ascending=False)
                for stock_code, score in filtered_scores.head(10).items():
                    print(f"  {stock_code}: 得分={score:.1f} (上市天数不足)")
            
            valid_stocks = valid_stocks & listing_filter
            print(f"[策略] 应用上市过滤后: {valid_stocks.sum()}")
        
        result_scores = scores[valid_stocks]
        
        return result_scores.sort_values(ascending=False)
    
    def filter_buy_list(self, buy_scores, date, max_count=MAX_POSITIONS):
        """
        过滤买入列表
        
        Args:
            buy_scores: 买入得分Series
            date: 日期
            max_count: 最大买入数量
            
        Returns:
            list: 过滤后的股票列表
        """
        stock_list = buy_scores.index.tolist()
        
        stock_list = filter_st_stocks(stock_list, date, self.his_st_dict)
        
        stock_list = stock_list[:max_count]
        
        return stock_list
    
    def check_exit_conditions(self, stock_code, holding_dict, current_price, current_date):
        metadata = self.metadata_mgr.get_metadata(stock_code)
        
        if not metadata:
            buy_price = holding_dict['cost']
            pct_change = (current_price - buy_price) / buy_price
            
            if pct_change >= 0.02:
                return True, 'target_profit_no_metadata'
            
            if pct_change <= STOP_LOSS:
                return True, 'stop_loss_no_metadata'
            
            return False, None
        
        buy_price = holding_dict['cost']
        target_profit = metadata['target_profit']
        
        if isinstance(metadata['buy_date'], str):
            buy_date = datetime.strptime(metadata['buy_date'], '%Y%m%d')
        else:
            buy_date = metadata['buy_date']
        
        if isinstance(current_date, str):
            current_date = datetime.strptime(current_date, '%Y%m%d')
        
        hold_days = (current_date - buy_date).days
        
        pct_change = (current_price - buy_price) / buy_price
        
        if pct_change >= target_profit:
            return True, 'target_profit'
        
        if pct_change <= STOP_LOSS:
            return True, 'stop_loss'
        
        if hold_days > MAX_HOLD_DAYS:
            return True, 'max_hold_days'
        
        return False, None
    
    def generate_sell_signals(self, current_prices, current_date, holdings_dict=None):
        """
        生成卖出信号
        
        Args:
            current_prices: 当前价格字典 {stock_code: price}
            current_date: 当前日期
            holdings_dict: 持仓字典 {stock_code: {'cost': xxx, 'volume': xxx, ...}}
                          如果为None，则使用position_wrapper获取
            
        Returns:
            dict: {stock_code: reason}
        """
        if holdings_dict is None:
            if self.position_wrapper is None:
                return {}
            holdings_dict = {}
            pos_dict = self.position_wrapper.get_position_dict()
            for stock_code, pos in pos_dict.items():
                holdings_dict[stock_code] = {
                    'cost': pos.m_dOpenPrice,
                    'volume': pos.m_nVolume,
                    'available': pos.m_nCanUseVolume
                }
        
        exit_dict = {}
        
        for stock_code in list(holdings_dict.keys()):
            if stock_code in current_prices:
                current_price = current_prices[stock_code]
                should_exit, reason = self.check_exit_conditions(
                    stock_code, holdings_dict[stock_code], current_price, current_date
                )
                if should_exit:
                    exit_dict[stock_code] = reason
        
        return exit_dict
    
    def calc_buy_amount(self, stock_code, total_capital, date):
        """
        计算买入金额
        
        Args:
            stock_code: 股票代码
            total_capital: 总资金
            date: 日期
            
        Returns:
            tuple: (amount, score)
        """
        if date not in self.score_df.index:
            return 0, 0
        
        score = self.score_df.loc[date, stock_code]
        
        if pd.isna(score) or score < 8:
            return 0, 0
        
        score = int(score)
        if score % 2 != 0:
            score = score - 1
        
        score = max(8, min(20, score))
        
        amount = self.metadata_mgr.calc_position_size(score, total_capital)
        
        return amount, score
    
    def on_buy(self, stock_code, date, score, buy_time=None):
        """
        买入成功回调
        
        Args:
            stock_code: 股票代码
            date: 买入日期
            score: 得分
            buy_time: 买入时间戳（datetime，可选）
        """
        self.metadata_mgr.add_metadata(stock_code, date, score, buy_time)
    
    def on_sell(self, stock_code):
        """
        卖出成功回调
        
        Args:
            stock_code: 股票代码
        """
        self.metadata_mgr.remove_metadata(stock_code)
    
    def get_holdings(self):
        """
        获取当前持仓（从真实持仓数据源）
        
        Returns:
            dict: 持仓字典 {stock_code: {'cost': xxx, 'volume': xxx, ...}}
        """
        if self.position_wrapper is None:
            return {}
        
        holdings_dict = {}
        pos_dict = self.position_wrapper.get_position_dict()
        for stock_code, pos in pos_dict.items():
            holdings_dict[stock_code] = {
                'cost': pos.m_dOpenPrice,
                'volume': pos.m_nVolume,
                'available': pos.m_nCanUseVolume,
                'float_profit': pos.m_dFloatProfit
            }
        return holdings_dict
    
    def get_position_count(self):
        """
        获取持仓数量
        
        Returns:
            int: 持仓数量
        """
        if self.position_wrapper is None:
            return len(self.metadata_mgr.get_all_metadata())
        return len(self.position_wrapper.get_position_dict())
    
    def sync_metadata_with_holdings(self):
        """
        对账：同步元数据与真实持仓
        
        清理已卖出但元数据未删除的股票
        检测并预警缺少元数据的持仓
        
        建议调用时机：每个bar开始时
        
        Returns:
            dict: {'removed': int, 'missing': int}
        """
        if self.position_wrapper is None:
            return {'removed': 0, 'missing': 0}
        
        real_holdings = self.position_wrapper.get_position_dict()
        metadata_holdings = self.metadata_mgr.get_all_metadata()
        
        removed_count = 0
        for stock_code in list(metadata_holdings.keys()):
            if stock_code not in real_holdings:
                self.metadata_mgr.remove_metadata(stock_code)
                removed_count += 1
        
        missing_count = 0
        for stock_code in real_holdings.keys():
            if stock_code not in metadata_holdings:
                missing_count += 1
        
        if removed_count > 0:
            print(f"[对账] 清理 {removed_count} 条元数据（持仓已不存在）")
        if missing_count > 0:
            print(f"[对账警告] {missing_count} 个持仓缺少元数据，将使用保守退出策略")
        
        return {'removed': removed_count, 'missing': missing_count}
