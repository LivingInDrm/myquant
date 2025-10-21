
def init(C):
    """初始化"""
    pass

def handlebar(C):
    """主策略逻辑"""
    if C.barpos <= 1:  # 09:30 第一根K线
        account = C.accounts['backtest'][0]
        stock_code = '000839.SZ'  # 测试股票
        
        # 获取市价
        kline = C.get_market_data(['close'], stock_code_list=[stock_code], period='1m', count=1)
        if kline and stock_code in kline['close']:
            price = kline['close'][stock_code][0]
            volume = 7900
            
            # 使用不同的 prType
            from xtquant.qmttools.functions import passorder
            passorder(
                23,                # 买入
                1102,              # 股票买入
                account,
                stock_code,
                44,    # 不同的价格类型
                float(price * 1.005),  # 价格+0.5%
                volume,
                'market_price',
                1,
                'test_market_price',
                C
            )
            
            print(f"[{strategy_name}] prType={prtype_value}, 下单: {stock_code}, 价格={price:.2f}, 数量={volume}")
