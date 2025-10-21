# coding: utf-8


class PositionDataWrapper:
    """
    持仓数据包装器
    
    封装 get_trade_detail_data 的 POSITION 查询，提供简化的持仓数据访问接口。
    本类只做数据透传，不包含任何业务逻辑处理。
    
    核心职责：
        - 统一管理账户和策略名称参数
        - 简化持仓数据的获取调用
        - 提供多种查询方式（列表、字典、单个股票）
    
    使用场景：
        - 回测模式下获取当前持仓信息
        - 查询指定股票的持仓详情
        - 遍历所有持仓进行批量操作
    
    典型用法：
        wrapper = PositionDataWrapper('test_account', 'momentum_strategy')
        
        # 方式1: 获取所有持仓列表
        positions = wrapper.get_all_positions()
        for pos in positions:
            print(f"{pos.m_strInstrumentID}: {pos.m_nVolume}")
        
        # 方式2: 获取持仓字典（便于按股票代码查询）
        pos_dict = wrapper.get_position_dict()
        if '600000.SH' in pos_dict:
            print(pos_dict['600000.SH'].m_nVolume)
        
        # 方式3: 直接查询单个股票
        pos = wrapper.get_position('600000.SH')
        if pos:
            print(f"持仓: {pos.m_nVolume}, 可用: {pos.m_nCanUseVolume}")
    
    注意事项：
        - 仅支持回测模式（依赖 get_trade_detail_data API）
        - 返回的是 DetailData 对象，需要通过 m_* 属性访问字段
        - 持仓数据为实时快照，每次调用都会重新查询
    """
    
    def __init__(self, account, strategy_name=''):
        """
        初始化持仓数据包装器
        
        Args:
            account: 账户ID（字符串），如 'test_account'
            strategy_name: 策略名称（字符串），用于过滤特定策略的持仓。
                          默认为空字符串，表示查询该账户下所有策略的持仓
        
        示例：
            wrapper = PositionDataWrapper('test_account', 'momentum_strategy')
        """
        self.account = account
        self.strategy_name = strategy_name
    
    def get_all_positions(self):
        """
        获取所有持仓的原始数据列表
        
        直接透传 get_trade_detail_data(account, 'stock', 'POSITION', strategy_name) 的返回值。
        
        Returns:
            list[DetailData]: 持仓对象列表，每个对象包含以下关键字段：
                - m_strInstrumentID: 股票代码（不含交易所后缀），如 '600000'
                - m_strExchangeID: 交易所代码，如 'SH'、'SZ'
                - m_nVolume: 持仓总数量（股）
                - m_nCanUseVolume: 可用数量（股），受 T+1 限制影响
                - m_dOpenPrice: 持仓成本价（元）
                - m_dFloatProfit: 浮动盈亏（元）
            
            如果无持仓或导入失败，返回空列表 []
        
        使用示例：
            positions = wrapper.get_all_positions()
            for pos in positions:
                code = f"{pos.m_strInstrumentID}.{pos.m_strExchangeID}"
                print(f"{code}: 总量={pos.m_nVolume}, 可用={pos.m_nCanUseVolume}")
        """
        try:
            from xtquant.qmttools.functions import get_trade_detail_data
        except ImportError:
            return []
        
        return get_trade_detail_data(
            self.account, 
            'stock', 
            'POSITION', 
            self.strategy_name
        )
    
    def get_position_dict(self):
        """
        获取持仓字典（便于按股票代码快速查询）
        
        将持仓列表转换为字典格式，key 为完整股票代码（含交易所后缀），value 为 DetailData 对象。
        
        Returns:
            dict: 持仓字典，格式为 {stock_code: DetailData}
                - key: 完整股票代码，如 '600000.SH'、'000001.SZ'
                - value: DetailData 对象（与 get_all_positions 返回的对象相同）
            
            如果无持仓，返回空字典 {}
        
        使用示例：
            pos_dict = wrapper.get_position_dict()
            
            # 检查是否持有某只股票
            if '600000.SH' in pos_dict:
                pos = pos_dict['600000.SH']
                print(f"持仓成本: {pos.m_dOpenPrice:.2f}")
            
            # 遍历所有持仓
            for code, pos in pos_dict.items():
                profit_pct = pos.m_dFloatProfit / (pos.m_nVolume * pos.m_dOpenPrice) * 100
                print(f"{code}: 盈亏比例={profit_pct:.2f}%")
        """
        positions = self.get_all_positions()
        
        position_dict = {}
        for pos in positions:
            stock_code = f"{pos.m_strInstrumentID}.{pos.m_strExchangeID}"
            position_dict[stock_code] = pos
        
        return position_dict
    
    def get_position(self, stock_code):
        """
        获取指定股票的持仓数据
        
        Args:
            stock_code: 完整股票代码（含交易所后缀），如 '600000.SH'、'000001.SZ'
        
        Returns:
            DetailData or None: 
                - 如果持有该股票，返回 DetailData 对象
                - 如果未持有该股票，返回 None
        
        使用示例：
            pos = wrapper.get_position('600000.SH')
            if pos:
                print(f"持仓数量: {pos.m_nVolume}")
                print(f"可用数量: {pos.m_nCanUseVolume}")
                print(f"成本价: {pos.m_dOpenPrice:.2f}")
                print(f"浮动盈亏: {pos.m_dFloatProfit:.2f}")
            else:
                print("未持有该股票")
        """
        position_dict = self.get_position_dict()
        return position_dict.get(stock_code, None)
