"""
测试不同 prType 对成交率的影响

对比三种价格类型：
- prType=11: 限价单（当前使用）
- prType=5:  最新价
- prType=44: 对手方最优价（市价单）
"""

from xtquant import xtdata
from xtquant.qmttools import run_strategy_file
import pandas as pd
import os

# 创建三个测试策略文件
strategies = {
    'limit_order': 11,      # 限价单
    'latest_price': 5,      # 最新价
    'market_price': 44,     # 对手价
}

test_dir = 'd:/program/myquant/test_prtype'
os.makedirs(test_dir, exist_ok=True)

for strategy_name, prtype_value in strategies.items():
    strategy_code = f'''
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
                {prtype_value},    # 不同的价格类型
                float(price * 1.005),  # 价格+0.5%
                volume,
                '{strategy_name}',
                1,
                'test_{strategy_name}',
                C
            )
            
            print(f"[{{strategy_name}}] prType={{prtype_value}}, 下单: {{stock_code}}, 价格={{price:.2f}}, 数量={{volume}}")
'''
    
    # 写入策略文件
    file_path = os.path.join(test_dir, f'{strategy_name}.py')
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(strategy_code)
    
    print(f"已创建策略文件: {file_path}")

print("\n" + "="*80)
print("策略文件创建完成！")
print("\n请手动运行回测，对比三种 prType 的成交情况：")
print("\n1. 修改 main_backtest.py 的 strategy_path 为以下路径：")
for name in strategies.keys():
    print(f"   - {test_dir}/{name}.py")
print("\n2. 分别运行回测，对比成交量和成交率")
print("\n3. 重点关注：")
print("   - 实际成交量")
print("   - 成交价格")
print("   - 是否全额成交")
print("="*80)
