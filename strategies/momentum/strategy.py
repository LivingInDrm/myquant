# coding: utf-8
import pandas as pd
import numpy as np
from datetime import datetime
from factors.factor_calculator import FactorCalculator
from .position_metadata import PositionMetadata
from core.position_data_wrapper import PositionDataWrapper
from utils.helpers import (
    filter_st_stocks, calc_minutes_since_open, 
    calc_daily_avg_volume_per_minute
)
from config.strategy_config import (
    BUY_CONDITION_1, BUY_CONDITION_2, MIN_LISTING_DAYS,
    DAILY_AVG_VOLUME_WINDOW_5D, DAILY_AVG_VOLUME_WINDOW_10D,
    STOP_LOSS, MAX_HOLD_DAYS
)


class MomentumStrategy:
    """短期强势股策略"""
    
    def __init__(self, account=None, strategy_name='', trade_executor=None):
        self.account = account
        self.strategy_name = strategy_name
        self.trade_executor = trade_executor
        
        self.factor_calc = FactorCalculator()
        self.metadata_mgr = PositionMetadata()
        self.position_wrapper = PositionDataWrapper(account, strategy_name) if account else None
        
        # 日频因子（用于分钟级评分的基础数据）
        self.open_df = None
        self.ma_dict = None
        self.rolling_max_dict = None
        self.buy_cond1_df = None
        
        # 成交量相关
        self.daily_avg_vol_per_min_5d = None
        self.daily_avg_volume_10d = None
        
        # 分钟级因子
        self.minute_cache = {}
        self.minute_scores = {}
        self.minute_buy_cond2 = {}
        
        # 过滤器
        self.his_st_dict = {}
        self.listing_filter_df = None
        
        # 交易日期索引
        self.trading_dates = []
        self.trading_date_to_idx = {}
    
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
        # 保留开盘价用于持仓市值估算
        self.open_df = open_df
        
        # 计算均线（用于分钟级评分）
        self.ma_dict = self.factor_calc.calc_ma(close_df, [5, 10, 20, 30, 60, 120])
        for period in self.ma_dict:
            self.ma_dict[period] = self.ma_dict[period].shift(1)
        
        # 计算滚动最高价（用于分钟级评分）
        self.rolling_max_dict = self.factor_calc.calc_rolling_max(
            high_df, [20, 40, 60, 80, 100]
        )
        for period in self.rolling_max_dict:
            self.rolling_max_dict[period] = self.rolling_max_dict[period].shift(1)
        
        # 计算买入条件1（日频）
        self.buy_cond1_df = self.factor_calc.calc_buy_condition_1(
            close_df,
            consecutive_days=BUY_CONDITION_1['consecutive_up_days'],
            or_days=BUY_CONDITION_1['or_days'],
            or_pct_change=BUY_CONDITION_1['or_pct_change']
        ).shift(1)
        
        # 计算5日平均每分钟成交量（用于分钟级量比计算）
        self.daily_avg_vol_per_min_5d = calc_daily_avg_volume_per_minute(
            volume_df, window=DAILY_AVG_VOLUME_WINDOW_5D
        ).shift(1)
        
        # 计算10日平均日成交量（用于分钟级成交量放大判断）
        self.daily_avg_volume_10d = volume_df.rolling(
            window=DAILY_AVG_VOLUME_WINDOW_10D, min_periods=DAILY_AVG_VOLUME_WINDOW_10D
        ).mean().shift(1)
        
        # 保存上市日期过滤器
        if listing_filter_df is not None:
            self.listing_filter_df = listing_filter_df
        
        # 构建交易日期索引（用于计算持仓天数）
        self.trading_dates = [pd.to_datetime(d).strftime('%Y%m%d') for d in close_df.index]
        self.trading_date_to_idx = {date: idx for idx, date in enumerate(self.trading_dates)}
    
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
    
    def update_minute_factors(self, date, minute_timestamp, minute_data):
        """
        更新分钟级因子（每分钟调用）
        
        Args:
            date: 日期（字符串或datetime对象）
            minute_timestamp: 分钟时间戳（datetime）
            minute_data: 当前时刻的分钟K线数据字典 {stock_code: {open, high, low, close, volume, amount, ...}}
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
        
        for stock_code, stock_data in minute_data.items():
            if stock_code not in self.minute_cache:
                continue
            
            price = stock_data.get('close', np.nan)
            volume = stock_data.get('volume', 0)
            amount = stock_data.get('amount', 0)
            
            if pd.isna(price) or price <= 0:
                continue
            
            # 先累加当前分钟的成交量和成交额
            self.minute_cache[stock_code]['cum_volume'] += volume
            self.minute_cache[stock_code]['cum_amount'] += amount
            
            # 获取累加后的值（截止当前分钟结束的累计量）
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
                if stock_code not in self.daily_avg_volume_10d.columns:
                    continue
                avg_volume_10d = self.daily_avg_volume_10d.loc[date, stock_code]
                if pd.isna(avg_volume_10d) or avg_volume_10d <= 0:
                    avg_volume_10d = 1
            except (KeyError, IndexError):
                avg_volume_10d = 1
            
            score = self.factor_calc.calc_minute_score(
                price, cum_volume, daily_ma, daily_rolling_max, avg_volume_10d
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
            buy_date_str = metadata['buy_date']
        else:
            buy_date_str = metadata['buy_date'].strftime('%Y%m%d') if isinstance(metadata['buy_date'], datetime) else str(metadata['buy_date'])
        
        if isinstance(current_date, datetime):
            current_date_str = current_date.strftime('%Y%m%d')
        else:
            current_date_str = str(current_date)
        
        if buy_date_str in self.trading_date_to_idx and current_date_str in self.trading_date_to_idx:
            hold_days = self.trading_date_to_idx[current_date_str] - self.trading_date_to_idx[buy_date_str]
        else:
            hold_days = 0
        
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
    
    def process_sell_orders(self, open_prices, current_datetime):
        """
        处理卖出信号并执行交易
        
        Args:
            open_prices: {股票代码: 开盘价}
            current_datetime: 当前时间（datetime对象）
        
        Returns:
            dict: 卖出后的持仓字典
        """
        if self.trade_executor is None:
            raise ValueError("未设置trade_executor，请先调用set_trade_executor()")
        
        holdings = self.trade_executor.get_holdings(self.account)
        
        if not holdings or not open_prices:
            return holdings
        
        current_date = current_datetime.strftime('%Y%m%d')
        current_time_str = current_datetime.strftime('%H:%M')
        
        exit_dict = self.generate_sell_signals(open_prices, current_date, holdings_dict=holdings)
        
        if not exit_dict:
            return holdings
        
        print(f"\n[{current_time_str}] 卖出信号: {len(exit_dict)} 只股票")
        
        for stock_code, reason in exit_dict.items():
            if stock_code not in holdings:
                continue
            
            holding = holdings[stock_code]
            available_volume = holding.get('available', 0)
            
            if available_volume <= 0:
                continue
            
            open_price = open_prices.get(stock_code, 0)
            if open_price <= 0:
                continue
            
            total_volume = holding['volume']
            print(f"  [{current_time_str}] 卖出 {stock_code}: 开盘价={open_price:.2f}, 数量={available_volume}, 原因={reason} (总持仓={total_volume})")
            
            self.trade_executor.sell(
                self.account, stock_code, open_price, available_volume,
                self.strategy_name, f'sell_{reason}'
            )
            
            self.on_sell(stock_code)
        
        holdings = self.trade_executor.get_holdings(self.account)
        cash = self.trade_executor.get_cash(self.account)
        print(f"  [{current_time_str}] 卖出后持仓数: {len(holdings)}, 可用资金: {cash:.2f}")
        
        return holdings
    
    def process_buy_orders(self, open_prices, current_datetime):
        """
        处理买入信号并执行交易
        
        Args:
            open_prices: {股票代码: 当前分钟开盘价}
            current_datetime: 当前时间（datetime对象）
        
        Returns:
            int: 买入股票数量
        """
        if self.trade_executor is None:
            raise ValueError("未设置trade_executor，请先调用set_trade_executor()")
        
        current_hour = current_datetime.hour
        current_minute = current_datetime.minute
        current_time_value = current_hour * 60 + current_minute
        if current_time_value < 10 * 60:
            return 0
        
        current_cash = self.trade_executor.get_cash(self.account)
        
        if current_cash < 10000:
            return 0
        
        current_date = current_datetime.strftime('%Y%m%d')
        buy_scores = self.generate_buy_signals_minute(current_date)
        
        if len(buy_scores) == 0:
            return 0
        
        current_holdings = self.trade_executor.get_holdings(self.account)
        existing_codes = set(current_holdings.keys())
        
        total_capital = self.trade_executor.get_total_asset(self.account)
        
        buy_count = 0
        
        for stock_code in buy_scores.index:
            if stock_code in existing_codes:
                continue
            
            if current_cash < 10000:
                break
            
            open_price = open_prices.get(stock_code, 0)
            if open_price <= 0:
                continue
            
            buy_amount, score = self.calc_buy_amount(stock_code, total_capital)
            
            if buy_amount > current_cash * 0.95:
                buy_amount = current_cash * 0.95
            
            if buy_amount < 10000:
                continue
            
            volume = int(buy_amount / open_price / 100) * 100
            
            if volume >= 100:
                self.trade_executor.buy(
                    self.account, stock_code, open_price, volume,
                    self.strategy_name, f'buy_score_{score}'
                )
                
                self.on_buy(stock_code, current_date, score, buy_time=current_datetime)
                
                current_cash = self.trade_executor.get_cash(self.account)
                current_holdings = self.trade_executor.get_holdings(self.account)
                existing_codes = set(current_holdings.keys())
                total_capital = self.trade_executor.get_total_asset(self.account)
                
                buy_count += 1
        
        return buy_count
    
    def calc_buy_amount(self, stock_code, total_capital):
        """
        计算买入金额（分钟级回测使用分钟级评分）
        
        Args:
            stock_code: 股票代码
            total_capital: 总资金
            
        Returns:
            tuple: (amount, score)
        """
        # 使用分钟级评分
        score = self.minute_scores.get(stock_code, None)
        
        if score is None:
            print(f"[WARNING] calc_buy_amount: {stock_code} 不在 minute_scores 中，跳过")
            return 0, 0
        
        if score < 8:
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
