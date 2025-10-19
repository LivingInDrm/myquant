# coding: utf-8
import pandas as pd
from datetime import datetime
from config.strategy_config import (
    POSITION_SIZE_MAP, TARGET_PROFIT_MAP, STOP_LOSS, MAX_HOLD_DAYS
)


class PositionManager:
    """仓位管理层，管理持仓和计算仓位"""
    
    def __init__(self):
        """初始化"""
        self.holdings = {}
    
    def calc_position_size(self, score, total_capital):
        """
        根据上涨趋势得分计算仓位大小
        
        Args:
            score: 上涨趋势得分 (8-20)
            total_capital: 总资金
            
        Returns:
            float: 买入金额
        """
        if score < 8:
            return 0
        
        position_pct = POSITION_SIZE_MAP.get(score, 0.02)
        
        return total_capital * position_pct
    
    def calc_target_profit(self, score):
        """
        根据得分计算目标收益率
        
        Args:
            score: 上涨趋势得分
            
        Returns:
            float: 目标收益率（小数形式）
        """
        if score < 8:
            return 0.02
        
        return TARGET_PROFIT_MAP.get(score, 0.02)
    
    def add_holding(self, stock_code, price, volume, date, score, buy_time=None):
        """
        添加持仓
        
        Args:
            stock_code: 股票代码
            price: 买入价格
            volume: 买入数量
            date: 买入日期
            score: 上涨趋势得分
            buy_time: 买入时间戳（datetime，可选，用于分钟级回测）
        """
        self.holdings[stock_code] = {
            'buy_price': price,
            'volume': volume,
            'buy_date': date,
            'buy_time': buy_time,
            'score': score,
            'target_profit': self.calc_target_profit(score),
            'hold_days': 0
        }
    
    def update_holding(self, stock_code, current_date):
        """
        更新持仓信息
        
        Args:
            stock_code: 股票代码
            current_date: 当前日期
        """
        if stock_code in self.holdings:
            buy_date = self.holdings[stock_code]['buy_date']
            if isinstance(buy_date, str):
                buy_date = datetime.strptime(buy_date, '%Y%m%d')
            if isinstance(current_date, str):
                current_date = datetime.strptime(current_date, '%Y%m%d')
            
            days_diff = (current_date - buy_date).days
            self.holdings[stock_code]['hold_days'] = days_diff
    
    def remove_holding(self, stock_code):
        """
        移除持仓
        
        Args:
            stock_code: 股票代码
        """
        if stock_code in self.holdings:
            del self.holdings[stock_code]
    
    def get_holding(self, stock_code):
        """
        获取持仓信息
        
        Args:
            stock_code: 股票代码
            
        Returns:
            dict: 持仓信息
        """
        return self.holdings.get(stock_code, None)
    
    def get_all_holdings(self):
        """
        获取所有持仓
        
        Returns:
            dict: 所有持仓
        """
        return self.holdings.copy()
    
    def check_exit_conditions(self, stock_code, current_price, current_date):
        """
        检查是否满足卖出条件
        
        卖出条件：
        1. 目标收益达成
        2. 止损：跌破成本价-3%
        3. 持仓超期：>3个交易日
        
        Args:
            stock_code: 股票代码
            current_price: 当前价格
            current_date: 当前日期
            
        Returns:
            tuple: (should_exit, reason)
        """
        if stock_code not in self.holdings:
            return False, None
        
        holding = self.holdings[stock_code]
        buy_price = holding['buy_price']
        target_profit = holding['target_profit']
        
        self.update_holding(stock_code, current_date)
        hold_days = holding['hold_days']
        
        pct_change = (current_price - buy_price) / buy_price
        
        if pct_change >= target_profit:
            return True, 'target_profit'
        
        if pct_change <= STOP_LOSS:
            return True, 'stop_loss'
        
        if hold_days > MAX_HOLD_DAYS:
            return True, 'max_hold_days'
        
        return False, None
    
    def check_all_exit_conditions(self, current_prices, current_date):
        """
        检查所有持仓的卖出条件
        
        Args:
            current_prices: 当前价格字典 {stock_code: price}
            current_date: 当前日期
            
        Returns:
            dict: {stock_code: reason} 需要卖出的股票及原因
        """
        exit_dict = {}
        
        for stock_code in list(self.holdings.keys()):
            if stock_code in current_prices:
                current_price = current_prices[stock_code]
                should_exit, reason = self.check_exit_conditions(
                    stock_code, current_price, current_date
                )
                if should_exit:
                    exit_dict[stock_code] = reason
        
        return exit_dict
    
    def get_position_count(self):
        """
        获取当前持仓数量
        
        Returns:
            int: 持仓股票数量
        """
        return len(self.holdings)
    
    def get_total_market_value(self, current_prices):
        """
        计算持仓市值
        
        Args:
            current_prices: 当前价格字典
            
        Returns:
            float: 总市值
        """
        total_value = 0
        for stock_code, holding in self.holdings.items():
            if stock_code in current_prices:
                volume = holding['volume']
                price = current_prices[stock_code]
                total_value += volume * price
        
        return total_value
    
    def get_unrealized_pnl(self, current_prices):
        """
        计算浮动盈亏
        
        Args:
            current_prices: 当前价格字典
            
        Returns:
            dict: {stock_code: pnl}
        """
        pnl_dict = {}
        for stock_code, holding in self.holdings.items():
            if stock_code in current_prices:
                buy_price = holding['buy_price']
                volume = holding['volume']
                current_price = current_prices[stock_code]
                pnl = (current_price - buy_price) * volume
                pnl_dict[stock_code] = pnl
        
        return pnl_dict
    
    def clear_holdings(self):
        """清空所有持仓"""
        self.holdings.clear()
