# coding: utf-8


class AccountDataWrapper:
    """
    账户资金数据包装器
    
    封装 get_trade_detail_data 的 account 查询，提供简化的账户资金访问接口。
    本类只做数据透传，不包含任何业务逻辑处理。
    
    核心职责：
        - 统一管理账户和策略名称参数
        - 简化资金数据的获取调用
        - 提供常用资金字段的快捷访问方法
    
    使用场景：
        - 回测模式下查询可用资金
        - 获取账户总资产和持仓市值
        - 计算资金使用率和风险敞口
    
    典型用法：
        wrapper = AccountDataWrapper('test_account', 'momentum_strategy')
        
        # 方式1: 获取原始账户数据对象
        account_data = wrapper.get_account_data()
        if account_data:
            print(f"可用资金: {account_data.m_dAvailable}")
            print(f"总资产: {account_data.m_dTotalAsset}")
        
        # 方式2: 使用便捷方法直接获取常用字段
        cash = wrapper.get_available_cash()
        total = wrapper.get_total_asset()
        market_value = wrapper.get_market_value()
        
        # 计算资金使用率
        usage_rate = market_value / total if total > 0 else 0
        print(f"资金使用率: {usage_rate:.2%}")
    
    注意事项：
        - 仅支持回测模式（依赖 get_trade_detail_data API）
        - 返回的是 DetailData 对象，需要通过 m_* 属性访问字段
        - 账户数据为实时快照，每次调用都会重新查询
        - 如果查询失败，便捷方法会返回默认值（0.0），不会抛出异常
    """
    
    def __init__(self, account, strategy_name=''):
        """
        初始化账户资金数据包装器
        
        Args:
            account: 账户ID（字符串），如 'test_account'
            strategy_name: 策略名称（字符串），用于过滤特定策略的资金。
                          默认为空字符串，表示查询该账户下所有策略的资金
        
        示例：
            wrapper = AccountDataWrapper('test_account', 'momentum_strategy')
        """
        self.account = account
        self.strategy_name = strategy_name
    
    def get_account_data(self):
        """
        获取账户资金的原始数据对象
        
        直接透传 get_trade_detail_data(account, 'stock', 'account', strategy_name) 的返回值。
        由于账户数据返回的是列表，本方法会自动提取第一个元素。
        
        Returns:
            DetailData or None: 账户数据对象，包含以下关键字段：
                - m_dAvailable: 可用资金（元），可用于买入股票的现金
                - m_dTotalAsset: 总资产（元），包含现金 + 持仓市值
                - m_dMarketValue: 持仓市值（元），所有持仓的当前市值
                - m_dFrozenCash: 冻结资金（元），已下单但未成交占用的资金
                - m_dWithdraw: 可取资金（元），可以从账户取出的资金
            
            如果查询失败或无数据，返回 None
        
        使用示例：
            account_data = wrapper.get_account_data()
            if account_data:
                print(f"可用资金: {account_data.m_dAvailable:.2f}")
                print(f"总资产: {account_data.m_dTotalAsset:.2f}")
                print(f"持仓市值: {account_data.m_dMarketValue:.2f}")
                print(f"冻结资金: {account_data.m_dFrozenCash:.2f}")
                
                cash_ratio = account_data.m_dAvailable / account_data.m_dTotalAsset
                print(f"现金比例: {cash_ratio:.2%}")
        """
        try:
            from xtquant.qmttools.functions import get_trade_detail_data
        except ImportError:
            return None
        
        asset_list = get_trade_detail_data(
            self.account, 
            'stock', 
            'account', 
            self.strategy_name
        )
        
        if asset_list and len(asset_list) > 0:
            return asset_list[0]
        
        return None
    
    def get_available_cash(self):
        """
        获取可用资金
        
        可用资金是指当前可以用于买入股票的现金余额（扣除冻结资金）。
        
        Returns:
            float: 可用资金（元）
                - 正常情况：返回账户的 m_dAvailable 字段值
                - 查询失败：返回 0.0
        
        使用示例：
            cash = wrapper.get_available_cash()
            print(f"当前可用资金: {cash:.2f} 元")
            
            # 判断是否有足够资金买入
            buy_amount = 50000
            if cash >= buy_amount:
                print("资金充足，可以买入")
            else:
                print(f"资金不足，还需 {buy_amount - cash:.2f} 元")
        """
        account_data = self.get_account_data()
        
        if account_data:
            return account_data.m_dAvailable
        
        return 0.0
    
    def get_total_asset(self):
        """
        获取总资产
        
        总资产 = 可用资金 + 冻结资金 + 持仓市值。
        
        Returns:
            float: 总资产（元）
                - 正常情况：返回账户的 m_dTotalAsset 字段值
                - 查询失败：返回 0.0
        
        使用示例：
            total = wrapper.get_total_asset()
            print(f"账户总资产: {total:.2f} 元")
            
            # 计算账户收益率
            initial_capital = 1000000
            profit_rate = (total - initial_capital) / initial_capital
            print(f"累计收益率: {profit_rate:.2%}")
        """
        account_data = self.get_account_data()
        
        if account_data:
            return account_data.m_dTotalAsset
        
        return 0.0
    
    def get_market_value(self):
        """
        获取持仓市值
        
        持仓市值是指当前所有持仓股票的总市值（按最新价计算）。
        
        Returns:
            float: 持仓市值（元）
                - 正常情况：返回账户的 m_dMarketValue 字段值
                - 查询失败：返回 0.0
        
        使用示例：
            market_value = wrapper.get_market_value()
            print(f"当前持仓市值: {market_value:.2f} 元")
            
            # 计算仓位使用率
            total = wrapper.get_total_asset()
            if total > 0:
                position_rate = market_value / total
                print(f"仓位使用率: {position_rate:.2%}")
            
            # 计算现金和持仓的比例
            cash = wrapper.get_available_cash()
            print(f"现金: {cash:.2f} ({cash/(cash+market_value):.1%})")
            print(f"持仓: {market_value:.2f} ({market_value/(cash+market_value):.1%})")
        """
        account_data = self.get_account_data()
        
        if account_data:
            return account_data.m_dMarketValue
        
        return 0.0
