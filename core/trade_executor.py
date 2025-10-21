# coding: utf-8
from core.position_data_wrapper import PositionDataWrapper
from core.account_data_wrapper import AccountDataWrapper


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
            
            # Debug: 下单前打印关键信息（撮合参数/涨跌停/停牌/下单参数）
            try:
                holdings_before = self.get_holdings(account, C)
                pre_hold_vol = holdings_before.get(stock_code, {}).get('volume', 0)
            except Exception:
                holdings_before = {}
                pre_hold_vol = None
            try:
                inst = C.get_instrument_detail(stock_code)
                up_stop = inst.get('UpStopPrice', None)
                down_stop = inst.get('DownStopPrice', None)
            except Exception as e:
                up_stop = None
                down_stop = None
                print(f"[DEBUG] 获取 {stock_code} 涨跌停价失败: {e}")
            try:
                is_susp = C.is_suspended_stock(stock_code, 1)
            except Exception as e:
                is_susp = None
                print(f"[DEBUG] 检查 {stock_code} 停牌状态失败: {e}")
            try:
                print(
                    f"[DEBUG] BUY passorder即将提交: code={stock_code}, price={price:.4f}, vol={volume}, "
                    f"quickTrade=0, prType=11(限价), strategy={strategy_name}, remark={remark}"
                )
                print(
                    f"[DEBUG] BacktestParams: slippage_type={getattr(C, 'slippage_type', None)}, "
                    f"slippage={getattr(C, 'slippage', None)}, max_vol_rate={getattr(C, 'max_vol_rate', None)}"
                )
                print(
                    f"[DEBUG] ContextInfo: period={getattr(C, 'period', None)}, "
                    f"barpos={getattr(C, 'barpos', None)}, "
                    f"bar_timetag={C.get_bar_timetag(C.barpos) if hasattr(C, 'barpos') else None}"
                )
                print(
                    f"[DEBUG] GuardInfo: up_stop={up_stop}, down_stop={down_stop}, is_suspended={is_susp}"
                )
            except Exception as e:
                print(f"[DEBUG] 预下单日志失败: {e}")

            order_id = passorder(
                23, 1101, account, stock_code, 11, float(price), volume,
                strategy_name, 0, remark, C
            )
            # Debug: 下单后立即回看该标的持仓
            try:
                holdings_after = self.get_holdings(account, C)
                if stock_code in holdings_after:
                    post_vol = holdings_after[stock_code].get('volume', 0)
                    avail = holdings_after[stock_code].get('available', 0)
                    print(f"[DEBUG] BUY后持仓: {stock_code} volume={post_vol}, available={avail}")
                    if pre_hold_vol is not None:
                        print(f"[DEBUG] BUY成交回看: 申报={volume}, 实际增持={post_vol - pre_hold_vol} (前持仓={pre_hold_vol})")
                else:
                    print(f"[DEBUG] BUY后持仓: {stock_code} 不在当前持仓中")
            except Exception as e:
                print(f"[DEBUG] BUY后查询持仓失败: {e}")
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
            
            # Debug: 下单前打印关键信息（撮合参数/涨跌停/停牌/下单参数）
            try:
                holdings_before = self.get_holdings(account, C)
                pre_hold_vol = holdings_before.get(stock_code, {}).get('volume', 0)
            except Exception:
                holdings_before = {}
                pre_hold_vol = None
            try:
                inst = C.get_instrument_detail(stock_code)
                up_stop = inst.get('UpStopPrice', None)
                down_stop = inst.get('DownStopPrice', None)
            except Exception as e:
                up_stop = None
                down_stop = None
                print(f"[DEBUG] 获取 {stock_code} 涨跌停价失败: {e}")
            try:
                is_susp = C.is_suspended_stock(stock_code, 1)
            except Exception as e:
                is_susp = None
                print(f"[DEBUG] 检查 {stock_code} 停牌状态失败: {e}")
            try:
                print(
                    f"[DEBUG] SELL passorder即将提交: code={stock_code}, price={price:.4f}, vol={volume}, "
                    f"quickTrade=0, prType=11(限价), strategy={strategy_name}, remark={remark}"
                )
                print(
                    f"[DEBUG] BacktestParams: slippage_type={getattr(C, 'slippage_type', None)}, "
                    f"slippage={getattr(C, 'slippage', None)}, max_vol_rate={getattr(C, 'max_vol_rate', None)}"
                )
                print(
                    f"[DEBUG] GuardInfo: up_stop={up_stop}, down_stop={down_stop}, is_suspended={is_susp}"
                )
            except Exception as e:
                print(f"[DEBUG] 预下单日志失败: {e}")

            order_id = passorder(
                24, 1101, account, stock_code, 11, float(price), volume,
                strategy_name, 0, remark, C
            )
            # Debug: 下单后立即回看该标的持仓
            try:
                holdings_after = self.get_holdings(account, C)
                if stock_code in holdings_after:
                    post_vol = holdings_after[stock_code].get('volume', 0)
                    avail = holdings_after[stock_code].get('available', 0)
                    print(f"[DEBUG] SELL后持仓: {stock_code} volume={post_vol}, available={avail}")
                    if pre_hold_vol is not None:
                        print(f"[DEBUG] SELL成交回看: 申报={volume}, 持仓变动={post_vol - pre_hold_vol} (前持仓={pre_hold_vol})")
                else:
                    print(f"[DEBUG] SELL后持仓: {stock_code} 不在当前持仓中")
            except Exception as e:
                print(f"[DEBUG] SELL后查询持仓失败: {e}")
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
            if C is None:
                return {}
            
            position_wrapper = PositionDataWrapper(account, 'momentum_strategy')
            result_list = position_wrapper.get_all_positions()
            
            holdings = {}
            for obj in result_list:
                stock_code = f"{obj.m_strInstrumentID}.{obj.m_strExchangeID}"
                holdings[stock_code] = {
                    'volume': obj.m_nVolume,
                    'cost': obj.m_dOpenPrice,
                    'float_profit': obj.m_dFloatProfit,
                    'available': obj.m_nCanUseVolume
                }
            
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
            if C is None:
                return 0
            
            account_wrapper = AccountDataWrapper(account, 'momentum_strategy')
            return account_wrapper.get_available_cash()
        
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
