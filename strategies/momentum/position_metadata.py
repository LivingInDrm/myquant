# coding: utf-8
from config.strategy_config import (
    POSITION_SIZE_MAP, TARGET_PROFIT_MAP, 
    DEFAULT_POSITION_SIZE, DEFAULT_TARGET_PROFIT
)


class PositionMetadata:
    
    def __init__(self):
        self.metadata = {}
    
    def calc_position_size(self, score, total_capital):
        position_pct = POSITION_SIZE_MAP.get(score, DEFAULT_POSITION_SIZE)
        
        return total_capital * position_pct
    
    def calc_target_profit(self, score):
        return TARGET_PROFIT_MAP.get(score, DEFAULT_TARGET_PROFIT)
    
    def add_metadata(self, stock_code, date, score, buy_time=None, buy_price=None, 
                    buy_volume=None, buy_amount=None, buy_fee=None, score_detail=None):
        self.metadata[stock_code] = {
            'buy_date': date,
            'buy_time': buy_time,
            'buy_price': buy_price,
            'buy_volume': buy_volume,
            'buy_amount': buy_amount,
            'buy_fee': buy_fee,
            'score': score,
            'score_detail': score_detail or {},
            'target_profit': self.calc_target_profit(score)
        }
    
    def remove_metadata(self, stock_code):
        if stock_code in self.metadata:
            del self.metadata[stock_code]
    
    def get_metadata(self, stock_code):
        return self.metadata.get(stock_code, None)
    
    def get_all_metadata(self):
        return self.metadata.copy()
    
    def clear_metadata(self):
        self.metadata.clear()
