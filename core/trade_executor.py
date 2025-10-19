# coding: utf-8


class TradeExecutor:
    """交易执行层，封装下单、撤单逻辑"""
    
    def __init__(self, mode='backtest'):
        """
        初始化
        
        Args:
            mode: 'backtest' 或 'realtime'
        """
        self.mode = mode
        self.xt_trader = None
    
    def set_xt_trader(self, xt_trader):
        """
        设置实盘交易对象
        
        Args:
            xt_trader: XtQuantTrader对象
        """
        self.xt_trader = xt_trader
    
    def buy(self, account, stock_code, price, volume, strategy_name='', remark='', C=None):
        """
        买入股票
        
        Args:
            account: 账户对象或账户ID
            stock_code: 股票代码
            price: 价格
            volume: 数量（股数）
            strategy_name: 策略名称
            remark: 备注
            C: 回测contextinfo对象（回测模式必须）
            
        Returns:
            订单ID或订单序号
        """
        if self.mode == 'backtest':
            if C is None:
                raise ValueError("回测模式必须提供contextinfo对象C")
            
            try:
                from xtquant.qmttools.functions import passorder
            except ImportError:
                print(f"[BACKTEST] BUY {stock_code} at {price:.2f}, volume={volume}")
                return None
            
            order_id = passorder(
                23, 1102, account, stock_code, 11, float(price), volume,
                strategy_name, 1, remark, C
            )
            return order_id
        
        elif self.mode == 'realtime':
            if self.xt_trader is None:
                raise ValueError("实盘模式必须先设置xt_trader")
            
            from xtquant import xtconstant
            
            order_id = self.xt_trader.order_stock(
                account, stock_code, xtconstant.STOCK_BUY, volume,
                xtconstant.FIX_PRICE, price, strategy_name, remark
            )
            return order_id
        
        else:
            raise ValueError(f"Unsupported mode: {self.mode}")
    
    def sell(self, account, stock_code, price, volume, strategy_name='', remark='', C=None):
        """
        卖出股票
        
        Args:
            account: 账户对象或账户ID
            stock_code: 股票代码
            price: 价格
            volume: 数量（股数）
            strategy_name: 策略名称
            remark: 备注
            C: 回测contextinfo对象（回测模式必须）
            
        Returns:
            订单ID或订单序号
        """
        if self.mode == 'backtest':
            if C is None:
                raise ValueError("回测模式必须提供contextinfo对象C")
            
            try:
                from xtquant.qmttools.functions import passorder
            except ImportError:
                print(f"[BACKTEST] SELL {stock_code} at {price:.2f}, volume={volume}")
                return None
            
            order_id = passorder(
                24, 1101, account, stock_code, 11, float(price), volume,
                strategy_name, 1, remark, C
            )
            return order_id
        
        elif self.mode == 'realtime':
            if self.xt_trader is None:
                raise ValueError("实盘模式必须先设置xt_trader")
            
            from xtquant import xtconstant
            
            order_id = self.xt_trader.order_stock(
                account, stock_code, xtconstant.STOCK_SELL, volume,
                xtconstant.FIX_PRICE, price, strategy_name, remark
            )
            return order_id
        
        else:
            raise ValueError(f"Unsupported mode: {self.mode}")
    
    def get_holdings(self, account, C=None):
        """
        获取持仓
        
        Args:
            account: 账户对象或账户ID
            C: 回测contextinfo对象（回测模式可选）
            
        Returns:
            dict: {stock_code: {'volume': xxx, 'cost': xxx, ...}}
        """
        if self.mode == 'backtest':
            print(f"[DEBUG] get_holdings调用 - account={account}, C={C is not None}")
            
            if C is None:
                print("[DEBUG] C为None，返回空字典")
                return {}
            
            try:
                from xtquant.qmttools.functions import get_trade_detail_data
                print("[DEBUG] 成功导入get_trade_detail_data")
            except ImportError as e:
                print(f"[DEBUG] 导入失败: {e}")
                return {}
            
            print(f"[DEBUG] 调用get_trade_detail_data(account={account}, type='stock', category='POSITION', strategy='momentum_strategy')")
            result_list = get_trade_detail_data(account, 'stock', 'POSITION', 'momentum_strategy')
            print(f"[DEBUG] result_list类型: {type(result_list)}, 长度: {len(result_list) if result_list else 0}")
            
            holdings = {}
            for obj in result_list:
                stock_code = f"{obj.m_strInstrumentID}.{obj.m_strExchangeID}"
                holdings[stock_code] = {
                    'volume': obj.m_nVolume,
                    'cost': obj.m_dOpenPrice,
                    'float_profit': obj.m_dFloatProfit,
                    'available': obj.m_nCanUseVolume
                }
            
            print(f"[DEBUG] 解析后的持仓: {holdings}")
            return holdings
        
        elif self.mode == 'realtime':
            if self.xt_trader is None:
                raise ValueError("实盘模式必须先设置xt_trader")
            
            positions = self.xt_trader.query_stock_positions(account)
            
            holdings = {}
            for pos in positions:
                holdings[pos.stock_code] = {
                    'volume': pos.volume,
                    'cost': pos.avg_price,
                    'available': pos.can_use_volume
                }
            
            return holdings
        
        else:
            raise ValueError(f"Unsupported mode: {self.mode}")
    
    def get_cash(self, account, C=None):
        """
        获取可用资金
        
        Args:
            account: 账户对象或账户ID
            C: 回测contextinfo对象（回测模式可选）
            
        Returns:
            float: 可用资金
        """
        if self.mode == 'backtest':
            print(f"[DEBUG] get_cash调用 - account={account}, C={C is not None}")
            
            if C is None:
                print("[DEBUG] C为None，返回0")
                return 0
            
            try:
                from xtquant.qmttools.functions import get_trade_detail_data
                print("[DEBUG] 成功导入get_trade_detail_data")
            except ImportError as e:
                print(f"[DEBUG] 导入失败: {e}")
                return 0
            
            print(f"[DEBUG] 调用get_trade_detail_data(account={account}, type='stock', category='account', strategy='momentum_strategy')")
            asset = get_trade_detail_data(account, 'stock', 'account', 'momentum_strategy')
            
            print(f"[DEBUG] asset类型: {type(asset)}")
            print(f"[DEBUG] asset长度: {len(asset) if asset else 0}")
            
            if asset and len(asset) > 0:
                print(f"[DEBUG] asset[0]对象: {asset[0]}")
                print(f"[DEBUG] asset[0]的所有属性: {[attr for attr in dir(asset[0]) if not attr.startswith('_')]}")
                available = asset[0].m_dAvailable
                print(f"[DEBUG] m_dAvailable值: {available}")
                return available
            else:
                print("[DEBUG] asset为空或长度为0，返回0")
            return 0
        
        elif self.mode == 'realtime':
            if self.xt_trader is None:
                raise ValueError("实盘模式必须先设置xt_trader")
            
            asset = self.xt_trader.query_stock_asset(account)
            if asset:
                return asset.cash
            return 0
        
        else:
            raise ValueError(f"Unsupported mode: {self.mode}")
    
    def cancel_order(self, account, order_id, C=None):
        """
        撤单
        
        Args:
            account: 账户对象或账户ID
            order_id: 订单ID
            C: 回测contextinfo对象（回测模式可选）
            
        Returns:
            bool: 是否成功
        """
        if self.mode == 'backtest':
            print(f"[BACKTEST] Cancel order {order_id}")
            return True
        
        elif self.mode == 'realtime':
            if self.xt_trader is None:
                raise ValueError("实盘模式必须先设置xt_trader")
            
            result = self.xt_trader.cancel_order_stock(account, order_id)
            return result == 0
        
        else:
            raise ValueError(f"Unsupported mode: {self.mode}")
