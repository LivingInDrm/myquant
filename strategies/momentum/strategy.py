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
from utils.logger import get_logger
from utils import trade_logger
from config.strategy_config import (
    BUY_CONDITION_1, BUY_CONDITION_2, MIN_LISTING_DAYS,
    DAILY_AVG_VOLUME_WINDOW_5D, DAILY_AVG_VOLUME_WINDOW_10D,
    STOP_LOSS, MAX_HOLD_DAYS, MIN_SCORE_THRESHOLD, DEFAULT_TARGET_PROFIT
)


class MomentumStrategy:
    """短期强势股策略"""
    
    def __init__(self, account=None, strategy_name='', trade_executor=None, logger=None):
        self.account = account
        self.strategy_name = strategy_name
        self.trade_executor = trade_executor
        self.logger = logger or get_logger('momentum')
        
        self.factor_calc = FactorCalculator()
        self.metadata_mgr = PositionMetadata()
        self.position_wrapper = PositionDataWrapper(account, strategy_name) if account else None
        
        # 日频因子（用于分钟级评分的基础数据）
        self.open_df = None
        self.ma_dict = None
        self.rolling_max_dict = None
        self.buy_cond1_df = None
        
        # 市场规则数据
        self.limit_up_df = None
        self.limit_down_df = None
        
        # 成交量相关
        self.daily_avg_vol_per_min_5d = None
        self.daily_avg_volume_10d = None
        
        # 分钟级因子
        self.minute_cache = {}
        self.minute_scores = {}
        self.minute_score_details = {}
        self.minute_buy_cond2 = {}
        
        # 过滤器
        self.his_st_dict = {}
        self.listing_filter_df = None
        
        # 交易日期索引
        self.trading_dates = []
        self.trading_date_to_idx = {}
        
        # 用于计算当日盈亏
        self.previous_day_assets = None
    
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
        
        from utils.market_rules import calculate_limit_prices
        self.limit_up_df, self.limit_down_df = calculate_limit_prices(
            close_df, 
            stock_list or close_df.columns.tolist()
        )
        
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
            date_str = date
        else:
            date_str = pd.to_datetime(date).strftime('%Y%m%d')
        
        if date_str not in self.daily_avg_vol_per_min_5d.index:
            return
        
        minutes_since_open = calc_minutes_since_open(minute_timestamp)
        if minutes_since_open <= 0:
            return
        
        # 预提取当天所有因子数据并转换为字典（避免循环内重复Series索引）
        day_avg_vol_5d = self.daily_avg_vol_per_min_5d.loc[date_str].to_dict()
        day_avg_vol_10d = self.daily_avg_volume_10d.loc[date_str].to_dict()
        
        day_limit_up = self.limit_up_df.loc[date_str].to_dict()
        day_limit_down = self.limit_down_df.loc[date_str].to_dict()
        
        day_ma = {}
        for period in [5, 10, 20, 30, 60, 120]:
            if period in self.ma_dict and date_str in self.ma_dict[period].index:
                day_ma[period] = self.ma_dict[period].loc[date_str].to_dict()
        
        day_rolling_max = {}
        for period in [20, 40, 60, 80, 100]:
            if period in self.rolling_max_dict and date_str in self.rolling_max_dict[period].index:
                day_rolling_max[period] = self.rolling_max_dict[period].loc[date_str].to_dict()
        
        for stock_code, stock_data in minute_data.items():
            if stock_code not in self.minute_cache:
                continue
            
            price = stock_data.get('close', np.nan)
            volume = stock_data.get('volume', 0)
            amount = stock_data.get('amount', 0)
            
            if pd.isna(price) or price <= 0:
                continue
            
            # 累加成交量和成交额
            self.minute_cache[stock_code]['cum_volume'] += volume
            self.minute_cache[stock_code]['cum_amount'] += amount
            
            cum_volume = self.minute_cache[stock_code]['cum_volume']
            cum_amount = self.minute_cache[stock_code]['cum_amount']
            
            avg_vol_per_min_5d = day_avg_vol_5d.get(stock_code)
            if avg_vol_per_min_5d is None or pd.isna(avg_vol_per_min_5d) or avg_vol_per_min_5d <= 0:
                continue
            
            volume_ratio = self.factor_calc.calc_intraday_volume_ratio(
                cum_volume, minutes_since_open, avg_vol_per_min_5d
            )
            
            buy_cond2 = self.factor_calc.calc_buy_condition_2_intraday(
                volume_ratio, cum_amount, minutes_since_open,
                early_minutes=BUY_CONDITION_2['early_minutes'],
                early_volume_ratio=BUY_CONDITION_2['early_volume_ratio'],
                early_amount=BUY_CONDITION_2['early_amount'],
                late_volume_ratio=BUY_CONDITION_2['late_volume_ratio'],
                late_amount=BUY_CONDITION_2['late_amount']
            )
            self.minute_buy_cond2[stock_code] = buy_cond2
            
            daily_ma = {}
            for period in [5, 10, 20, 30, 60, 120]:
                if period in day_ma:
                    val = day_ma[period].get(stock_code)
                    if val is not None:
                        daily_ma[period] = val
            
            daily_rolling_max = {}
            for period in [20, 40, 60, 80, 100]:
                if period in day_rolling_max:
                    val = day_rolling_max[period].get(stock_code)
                    if val is not None:
                        daily_rolling_max[period] = val
            
            if not daily_ma or not daily_rolling_max:
                continue
            
            avg_volume_10d = day_avg_vol_10d.get(stock_code, 1)
            if pd.isna(avg_volume_10d) or avg_volume_10d <= 0:
                avg_volume_10d = 1
            
            score, score_detail = self.factor_calc.calc_minute_score(
                price, cum_volume, daily_ma, daily_rolling_max, avg_volume_10d
            )
            self.minute_scores[stock_code] = score
            self.minute_score_details[stock_code] = score_detail
    
    def generate_buy_signals_minute(self, date):
        """
        生成买入信号（分钟级）
        
        Args:
            date: 日期（字符串或datetime对象）
            
        Returns:
            tuple: (买入信号Series, 漏斗统计字典)
                - 买入信号Series: 股票得分Series (得分>=MIN_SCORE_THRESHOLD的股票)
                - 漏斗统计: {'total': X, 'cond1': Y, 'cond2': Z, 'score': A, 'listing': B, 'min_score': MIN_SCORE_THRESHOLD}
        """
        if isinstance(date, str):
            date_str = date
        else:
            date_str = pd.to_datetime(date).strftime('%Y%m%d')
        
        funnel_stats = {
            'total': len(self.minute_scores),
            'cond1': 0,
            'cond2': 0,
            'score': 0,
            'listing': 0,
            'min_score': MIN_SCORE_THRESHOLD
        }
        
        if date_str not in self.buy_cond1_df.index:
            return pd.Series(dtype=float), funnel_stats
        
        cond1 = self.buy_cond1_df.loc[date_str]
        
        result_scores = pd.Series(dtype=float)
        
        for stock_code in self.minute_scores.keys():
            if stock_code not in cond1.index:
                continue
            
            if not cond1[stock_code]:
                continue
            
            funnel_stats['cond1'] += 1
            
            cond2 = self.minute_buy_cond2.get(stock_code, False)
            if not cond2:
                continue
            
            funnel_stats['cond2'] += 1
            
            score = self.minute_scores[stock_code]
            if score >= MIN_SCORE_THRESHOLD:
                funnel_stats['score'] += 1
                
                if self.listing_filter_df is not None and date_str in self.listing_filter_df.index:
                    if stock_code in self.listing_filter_df.columns:
                        if not self.listing_filter_df.loc[date_str, stock_code]:
                            continue
                
                result_scores[stock_code] = score
                funnel_stats['listing'] += 1
        
        return result_scores.sort_values(ascending=False), funnel_stats
    
    
    def check_exit_conditions(self, stock_code, holding_dict, current_price, current_date):
        metadata = self.metadata_mgr.get_metadata(stock_code)
        
        if not metadata:
            buy_price = holding_dict['cost']
            pct_change = (current_price - buy_price) / buy_price
            
            if pct_change >= DEFAULT_TARGET_PROFIT:
                return True, 'target_profit_no_metadata', {
                    'type': 'TAKE_PROFIT',
                    'pct': pct_change * 100,
                    'days': 0
                }
            
            if pct_change <= STOP_LOSS:
                return True, 'stop_loss_no_metadata', {
                    'type': 'STOP_LOSS',
                    'pct': pct_change * 100,
                    'days': 0
                }
            
            return False, None, None
        
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
            return True, 'target_profit', {
                'type': 'TAKE_PROFIT',
                'pct': pct_change * 100,
                'days': hold_days
            }
        
        if pct_change <= STOP_LOSS:
            return True, 'stop_loss', {
                'type': 'STOP_LOSS',
                'pct': pct_change * 100,
                'days': hold_days
            }
        
        if hold_days > MAX_HOLD_DAYS:
            return True, 'max_hold_days', {
                'type': 'MAX_DAYS',
                'pct': pct_change * 100,
                'days': hold_days,
                'limit': MAX_HOLD_DAYS
            }
        
        return False, None, None
    
    def generate_sell_signals(self, current_prices, current_date, holdings_dict=None):
        """
        生成卖出信号
        
        Args:
            current_prices: 当前价格字典 {stock_code: price}
            current_date: 当前日期
            holdings_dict: 持仓字典 {stock_code: {'cost': xxx, 'volume': xxx, ...}}
                          如果为None，则使用position_wrapper获取
            
        Returns:
            dict: {stock_code: (reason, reason_detail)}
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
                should_exit, reason, reason_detail = self.check_exit_conditions(
                    stock_code, holdings_dict[stock_code], current_price, current_date
                )
                if should_exit:
                    exit_dict[stock_code] = (reason, reason_detail)
        
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
        current_time_str = current_datetime.strftime('%Y%m%d %H:%M')
        
        exit_dict = self.generate_sell_signals(open_prices, current_date, holdings_dict=holdings)
        
        if not exit_dict:
            return holdings
        
        for stock_code, (reason, reason_detail) in exit_dict.items():
            if stock_code not in holdings:
                continue
            
            holding = holdings[stock_code]
            available_volume = holding.get('available', 0)
            
            if available_volume <= 0:
                continue
            
            open_price = open_prices.get(stock_code, 0)
            if open_price <= 0:
                continue
            
            metadata = self.metadata_mgr.get_metadata(stock_code)
            
            buy_info = {
                'price': metadata['buy_price'] if metadata and metadata.get('buy_price') else holding['cost'],
                'volume': metadata['buy_volume'] if metadata and metadata.get('buy_volume') else holding['volume'],
                'date': metadata['buy_date'] if metadata else 'unknown'
            }
            
            actual_amount = available_volume * open_price
            fee = max(actual_amount * 0.0003, 5) + actual_amount * 0.001
            
            sell_info = {
                'price': open_price,
                'volume': available_volume,
                'fee': fee
            }
            
            old_score = metadata['score'] if metadata else 0
            old_score_detail = metadata.get('score_detail', {}) if metadata else {}
            new_score = self.minute_scores.get(stock_code, 0)
            new_score_detail = self.minute_score_details.get(stock_code, {})
            
            score_change = {
                'old_score': old_score,
                'old_detail': old_score_detail,
                'new_score': new_score,
                'new_detail': new_score_detail
            }
            
            trade_logger.log_sell_trade(
                self.logger, current_time_str, stock_code, buy_info, 
                sell_info, reason_detail, score_change
            )
            
            self.trade_executor.sell(
                self.account, stock_code, open_price, available_volume,
                self.strategy_name, f'sell_{reason}'
            )
            
            self.on_sell(stock_code)
        
        return self.trade_executor.get_holdings(self.account)
    
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
        buy_scores, funnel_stats = self.generate_buy_signals_minute(current_date)
        
        current_time_str = current_datetime.strftime('%Y%m%d %H:%M')
        
        day_limit_up = {}
        day_limit_down = {}
        if current_date in self.limit_up_df.index:
            day_limit_up = self.limit_up_df.loc[current_date].to_dict()
            day_limit_down = self.limit_down_df.loc[current_date].to_dict()
        
        if len(buy_scores) == 0:
            trade_logger.log_buy_funnel(
                self.logger, current_time_str, funnel_stats, 0, current_cash
            )
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
                actual_amount = volume * open_price
                fee = max(actual_amount * 0.0003, 5)
                
                self.trade_executor.buy(
                    self.account, stock_code, open_price, volume,
                    self.strategy_name, f'buy_score_{score}'
                )
                
                score_detail = self.minute_score_details.get(stock_code, {})
                
                limit_prices = None
                limit_up = day_limit_up.get(stock_code)
                limit_down = day_limit_down.get(stock_code)
                if limit_up is not None and limit_down is not None:
                    limit_prices = {
                        'up_stop': limit_up,
                        'down_stop': limit_down
                    }
                
                trade_logger.log_buy_trade(
                    self.logger, current_time_str, stock_code, open_price, 
                    volume, actual_amount, fee, score, score_detail, limit_prices
                )
                
                self.on_buy(
                    stock_code, current_date, score, buy_time=current_datetime,
                    buy_price=open_price, buy_volume=volume, buy_amount=actual_amount,
                    buy_fee=fee, score_detail=score_detail
                )
                
                current_cash = self.trade_executor.get_cash(self.account)
                current_holdings = self.trade_executor.get_holdings(self.account)
                existing_codes = set(current_holdings.keys())
                total_capital = self.trade_executor.get_total_asset(self.account)
                
                buy_count += 1
        
        trade_logger.log_buy_funnel(
            self.logger, current_time_str, funnel_stats, buy_count, current_cash
        )
        
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
            self.logger.warning(f"calc_buy_amount: {stock_code} 不在 minute_scores 中，跳过")
            return 0, 0
        
        score = int(score)
        if score % 2 != 0:
            score = score - 1
        
        score = max(MIN_SCORE_THRESHOLD, min(20, score))
        
        amount = self.metadata_mgr.calc_position_size(score, total_capital)
        
        return amount, score
    
    def on_buy(self, stock_code, date, score, buy_time=None, buy_price=None, 
              buy_volume=None, buy_amount=None, buy_fee=None, score_detail=None):
        """
        买入成功回调
        
        Args:
            stock_code: 股票代码
            date: 买入日期
            score: 得分
            buy_time: 买入时间戳（datetime，可选）
            buy_price: 买入价格
            buy_volume: 买入数量
            buy_amount: 买入金额
            buy_fee: 手续费
            score_detail: 评分明细
        """
        self.metadata_mgr.add_metadata(
            stock_code, date, score, buy_time, buy_price, 
            buy_volume, buy_amount, buy_fee, score_detail
        )
    
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
            self.logger.info(f"[对账] 清理 {removed_count} 条元数据（持仓已不存在）")
        if missing_count > 0:
            self.logger.warning(f"{missing_count} 个持仓缺少元数据，将使用保守退出策略")
        
        return {'removed': removed_count, 'missing': missing_count}
    
    def log_daily_snapshot(self, current_datetime, current_prices):
        """
        记录每日持仓快照
        
        Args:
            current_datetime: 当前时间（datetime对象）
            current_prices: 当前价格字典 {stock_code: price}
        """
        if self.trade_executor is None:
            return
        
        current_date = current_datetime.strftime('%Y-%m-%d')
        
        total_assets = self.trade_executor.get_total_asset(self.account)
        cash = self.trade_executor.get_cash(self.account)
        holdings = self.trade_executor.get_holdings(self.account)
        position_count = len(holdings)
        
        if self.previous_day_assets is None:
            daily_pnl = 0
            daily_pnl_pct = 0
        else:
            daily_pnl = total_assets - self.previous_day_assets
            daily_pnl_pct = (daily_pnl / self.previous_day_assets * 100) if self.previous_day_assets > 0 else 0
        
        account_summary = {
            'total_assets': total_assets,
            'position_count': position_count,
            'cash': cash,
            'daily_pnl': daily_pnl,
            'daily_pnl_pct': daily_pnl_pct
        }
        
        position_details = []
        
        for stock_code, holding in holdings.items():
            metadata = self.metadata_mgr.get_metadata(stock_code)
            
            cost = holding['cost']
            current_price = current_prices.get(stock_code, cost)
            
            pnl_pct = (current_price - cost) / cost * 100 if cost > 0 else 0
            
            if metadata:
                buy_date_str = metadata['buy_date']
                if isinstance(buy_date_str, str):
                    pass
                elif isinstance(buy_date_str, datetime):
                    buy_date_str = buy_date_str.strftime('%Y%m%d')
                else:
                    buy_date_str = str(buy_date_str)
                
                current_date_str = current_datetime.strftime('%Y%m%d')
                
                if buy_date_str in self.trading_date_to_idx and current_date_str in self.trading_date_to_idx:
                    days = self.trading_date_to_idx[current_date_str] - self.trading_date_to_idx[buy_date_str]
                else:
                    days = 0
                
                score = self.minute_scores.get(stock_code, metadata.get('score', 0))
                score_detail = self.minute_score_details.get(stock_code, metadata.get('score_detail', {}))
            else:
                days = 0
                score = 0
                score_detail = {}
            
            volume = holding.get('volume', 0)
            amount = volume * current_price
            
            position_details.append({
                'stock_code': stock_code,
                'days': days,
                'cost': cost,
                'price': current_price,
                'volume': volume,
                'amount': amount,
                'pnl_pct': pnl_pct,
                'score': score,
                'score_detail': score_detail
            })
        
        trade_logger.log_daily_position_snapshot(
            self.logger, current_date, account_summary, position_details
        )
        
        self.previous_day_assets = total_assets
