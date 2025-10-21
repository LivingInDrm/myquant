# coding: utf-8
from config.strategy_config import POSITION_SIZE_MAP, TARGET_PROFIT_MAP


class PositionMetadata:
    
    def __init__(self):
        self.metadata = {}
    
    def calc_position_size(self, score, total_capital):
        if score < 8:
            return 0
        
        position_pct = POSITION_SIZE_MAP.get(score, 0.02)
        
        return total_capital * position_pct
    
    def calc_target_profit(self, score):
        if score < 8:
            return 0.02
        
        return TARGET_PROFIT_MAP.get(score, 0.02)
    
    def add_metadata(self, stock_code, date, score, buy_time=None):
        self.metadata[stock_code] = {
            'buy_date': date,
            'buy_time': buy_time,
            'score': score,
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
