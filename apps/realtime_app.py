# coding: utf-8
import sys
import os
import time
from datetime import datetime
import pandas as pd

# 添加项目根目录到 Python 路径，以便导入 xtquant 等模块
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
from xtquant import xtconstant, xtdata

from data.data_provider import DataProvider
from core.trade_executor import TradeExecutor
from strategies.momentum.strategy import MomentumStrategy
from utils.helpers import get_df_ex, filter_opendate
from config.strategy_config import MAX_POSITIONS


class MyXtQuantTraderCallback(XtQuantTraderCallback):
    """交易回调类"""
    
    def on_disconnected(self):
        print("连接断开")
    
    def on_stock_order(self, order):
        print(f"委托回报: {order.stock_code} {order.order_status} {order.order_sysid}")
    
    def on_stock_asset(self, asset):
        print(f"资金变动: {asset.account_id} 现金={asset.cash} 总资产={asset.total_asset}")
    
    def on_stock_trade(self, trade):
        print(f"成交回报: {trade.stock_code} 数量={trade.traded_volume} 价格={trade.traded_price}")
    
    def on_stock_position(self, position):
        print(f"持仓变动: {position.stock_code} 数量={position.volume}")
    
    def on_order_error(self, order_error):
        print(f"委托失败: {order_error.order_id} {order_error.error_msg}")
    
    def on_cancel_error(self, cancel_error):
        print(f"撤单失败: {cancel_error.order_id} {cancel_error.error_msg}")


class RealtimeTrading:
    """实盘交易类"""
    
    def __init__(self, qmt_path, session_id, account_id, stock_pool='沪深A股'):
        """
        初始化
        
        Args:
            qmt_path: QMT安装路径下的userdata_mini路径
            session_id: 会话ID
            account_id: 资金账号
            stock_pool: 股票池名称
        """
        self.qmt_path = qmt_path
        self.session_id = session_id
        self.account_id = account_id
        self.stock_pool = stock_pool
        
        self.xt_trader = None
        self.account = None
        
        self.data_provider = DataProvider(batch_size=500)
        self.trade_executor = TradeExecutor(mode='realtime', strategy_name='momentum_strategy')
        self.strategy = MomentumStrategy(account=account_id, strategy_name='momentum_strategy')
        
        self.stock_list = []
        self.last_update_date = None
    
    def initialize(self):
        """初始化交易连接"""
        print("=" * 60)
        print("初始化实盘交易系统")
        print("=" * 60)
        
        self.xt_trader = XtQuantTrader(self.qmt_path, self.session_id)
        self.account = StockAccount(self.account_id)
        
        callback = MyXtQuantTraderCallback()
        self.xt_trader.register_callback(callback)
        
        self.xt_trader.start()
        
        connect_result = self.xt_trader.connect()
        if connect_result != 0:
            print(f"连接失败: {connect_result}")
            return False
        print("连接成功")
        
        subscribe_result = self.xt_trader.subscribe(self.account)
        if subscribe_result != 0:
            print(f"订阅失败: {subscribe_result}")
            return False
        print("订阅成功")
        
        self.trade_executor.set_xt_trader(self.xt_trader)
        
        self.stock_list = self.data_provider.get_stock_list_in_sector(self.stock_pool)
        print(f"股票池: {self.stock_pool}, 股票数量: {len(self.stock_list)}")
        
        print("初始化完成")
        return True
    
    def update_factors(self, lookback_days=250):
        """
        更新因子数据
        
        Args:
            lookback_days: 回溯天数
        """
        print("=" * 60)
        print("更新因子数据")
        print("=" * 60)
        
        today = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - pd.Timedelta(days=lookback_days)).strftime('%Y%m%d')
        
        print(f"获取历史数据: {start_date} ~ {today}")
        
        data = self.data_provider.get_daily_data(
            stock_list=self.stock_list,
            start_time=start_date,
            end_time=today,
            dividend_type='front',
            fill_data=True
        )
        
        if not data:
            print("无法获取历史数据")
            return False
        
        close_df = get_df_ex(data, 'close')
        open_df = get_df_ex(data, 'open')
        high_df = get_df_ex(data, 'high')
        volume_df = get_df_ex(data, 'volume')
        amount_df = get_df_ex(data, 'amount')
        
        listing_filter_df = filter_opendate(self.stock_list, close_df, 120, 'xtdata')
        
        self.strategy.prepare_factors(
            close_df, open_df, high_df, volume_df, amount_df,
            stock_list=self.stock_list,
            listing_filter_df=listing_filter_df
        )
        
        self.last_update_date = today
        print("因子更新完成")
        return True
    
    def trade_daily(self):
        """执行每日交易"""
        today = datetime.now().strftime('%Y%m%d')
        
        if self.last_update_date != today:
            print(f"\n新交易日: {today}")
            if not self.update_factors():
                print("因子更新失败，跳过交易")
                return
        
        print("=" * 60)
        print(f"执行交易: {today}")
        print("=" * 60)
        
        self.strategy.sync_metadata_with_holdings()
        
        current_holdings = self.trade_executor.get_holdings(self.account)
        current_cash = self.trade_executor.get_cash(self.account)
        
        print(f"当前持仓数: {len(current_holdings)}, 可用资金: {current_cash:.2f}")
        
        current_prices = {}
        current_tick_data = {}
        for stock_code in self.stock_list:
            tick = xtdata.get_full_tick([stock_code])
            if stock_code in tick:
                price = tick[stock_code].get('lastPrice', 0)
                if price > 0:
                    current_prices[stock_code] = price
                    current_tick_data[stock_code] = tick[stock_code]
        
        exit_dict = self.strategy.generate_sell_signals(current_prices, today, holdings_dict=current_holdings)
        
        if exit_dict:
            print(f"\n卖出信号: {len(exit_dict)} 只股票")
            for stock_code, reason in exit_dict.items():
                if stock_code in current_holdings:
                    holding = current_holdings[stock_code]
                    volume = holding['available']
                    price = current_prices.get(stock_code, 0) * 0.999
                    
                    if price > 0 and volume > 0:
                        print(f"  卖出 {stock_code}: 价格={price:.2f}, 数量={volume}, 原因={reason}")
                        
                        self.trade_executor.sell(
                            self.account, stock_code, price, volume,
                            'momentum_strategy', f'sell_{reason}'
                        )
                        
                        self.strategy.on_sell(stock_code)
        
        time.sleep(2)
        
        current_holdings = self.trade_executor.get_holdings(self.account)
        current_cash = self.trade_executor.get_cash(self.account)
        
        available_slots = MAX_POSITIONS - len(current_holdings)
        
        # 时间过滤：09:35之前不交易
        now = datetime.now()
        current_time_value = now.hour * 60 + now.minute
        if current_time_value < 9 * 60 + 35:  # 9:35 = 575分钟
            print(f"[{now.strftime('%H:%M')}] 09:35之前不交易，跳过买入")
            return
        
        if available_slots > 0 and current_cash > 10000:
            print(f"\n生成买入信号...")
            buy_scores = self.strategy.generate_buy_signals(today)
            
            if len(buy_scores) > 0:
                buy_list = self.strategy.filter_buy_list(buy_scores, today, available_slots)
                
                existing_codes = set(current_holdings.keys())
                buy_list = [s for s in buy_list if s not in existing_codes]
                
                if buy_list:
                    print(f"买入信号: {len(buy_list)} 只股票")
                    
                    for stock_code in buy_list:
                        price = current_prices.get(stock_code, 0) * 1.001
                        
                        if price <= 0:
                            continue
                        
                        total_capital = current_cash + sum(
                            h['volume'] * current_prices.get(s, 0) 
                            for s, h in current_holdings.items()
                        )
                        
                        buy_amount, score = self.strategy.calc_buy_amount(
                            stock_code, total_capital, today
                        )
                        
                        if buy_amount > current_cash * 0.95:
                            buy_amount = current_cash * 0.95
                        
                        if buy_amount < 10000:
                            continue
                        
                        volume = int(buy_amount / price / 100) * 100
                        
                        if volume >= 100:
                            print(f"  买入 {stock_code}: 价格={price:.2f}, 数量={volume}, 得分={score}")
                            
                            print("=" * 60)
                            print(f"[买入前调试信息] {stock_code}")
                            print("-" * 60)
                            print(f"[股票信息]")
                            print(f"  代码: {stock_code}")
                            print(f"  价格: {price:.2f}")
                            print(f"  数量: {volume}")
                            print(f"  评分: {score:.2f}")
                            
                            print(f"[实时行情]")
                            if stock_code in current_tick_data:
                                tick = current_tick_data[stock_code]
                                print(f"  最新价: {tick.get('lastPrice', 0):.2f}")
                                print(f"  开盘价: {tick.get('open', 0):.2f}")
                                print(f"  最高价: {tick.get('high', 0):.2f}")
                                print(f"  最低价: {tick.get('low', 0):.2f}")
                                print(f"  成交量: {tick.get('volume', 0):,.0f}")
                                print(f"  成交额: {tick.get('amount', 0):,.2f}")
                                open_price = tick.get('open', 0)
                                high_price = tick.get('high', 0)
                                low_price = tick.get('low', 0)
                                if open_price > 0:
                                    print(f"  振幅: {((high_price - low_price) / open_price * 100):.2f}%")
                            else:
                                print("  无实时行情数据")
                            
                            holding_market_value = sum(
                                h['volume'] * current_prices.get(s, 0) 
                                for s, h in current_holdings.items()
                            )
                            
                            print(f"[账户信息]")
                            print(f"  可用资金: {current_cash:.2f}")
                            print(f"  总资产: {total_capital:.2f}")
                            print(f"  持仓市值: {holding_market_value:.2f}")
                            print(f"  资金使用率: {(holding_market_value/total_capital*100 if total_capital > 0 else 0):.2f}%")
                            
                            print(f"[持仓元数据]")
                            all_metadata = self.strategy.metadata_mgr.get_all_metadata()
                            if all_metadata:
                                for code, meta in all_metadata.items():
                                    print(f"  {code}: 买入日期={meta.get('buy_date')}, 评分={meta.get('score')}, 目标收益={meta.get('target_profit', 0)*100:.2f}%")
                            else:
                                print("  当前无持仓元数据")
                            
                            print(f"[当前持仓]")
                            if current_holdings:
                                for code, pos in current_holdings.items():
                                    print(f"  {code}: 数量={pos.get('volume', 0)}, 成本={pos.get('cost', 0):.2f}, 可用={pos.get('available', 0)}")
                            else:
                                print("  当前无持仓")
                            print("=" * 60)
                            
                            self.trade_executor.buy(
                                self.account, stock_code, price, volume,
                                'momentum_strategy', f'buy_score_{score}'
                            )
                            
                            self.strategy.on_buy(stock_code, today, score)
                            
                            current_cash -= volume * price
                            
                            if current_cash < 10000:
                                break
                        
                        time.sleep(1)
        
        print("交易执行完成")
    
    def run(self):
        """启动实盘交易"""
        if not self.initialize():
            print("初始化失败")
            return
        
        print("\n实盘交易系统已启动")
        print("按 Ctrl+C 停止")
        
        try:
            while True:
                now = datetime.now()
                
                if now.hour == 9 and now.minute == 35:
                    self.trade_daily()
                    time.sleep(60)
                
                time.sleep(10)
        
        except KeyboardInterrupt:
            print("\n停止交易")
        
        finally:
            if self.xt_trader:
                self.xt_trader.stop()
            print("系统已退出")


if __name__ == '__main__':
    QMT_PATH = r'D:\迅投极速交易终端 睿智融科版\userdata_mini'
    SESSION_ID = 123456
    ACCOUNT_ID = '1000000365'
    
    trading = RealtimeTrading(
        qmt_path=QMT_PATH,
        session_id=SESSION_ID,
        account_id=ACCOUNT_ID,
        stock_pool='沪深A股'
    )
    
    trading.run()
