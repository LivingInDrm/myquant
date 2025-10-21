# coding: utf-8
import sys
import io
import os

os.environ['PYTHONIOENCODING'] = 'utf-8'

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)

import pandas as pd
from xtquant import xtdata


class G():
    pass


g = G()


def init(C):
    """初始化函数"""
    print("=" * 60)
    print("初始化极简回测 - 用于排查成交问题")
    print("=" * 60)
    
    g.accid = 'test'
    g.money = 10000000
    
    g.target_stocks = [
        '000839.SZ',
        '002115.SZ',
        '002210.SZ',
        '002530.SZ',
        '002564.SZ'
    ]
    
    g.order_volume = 1000
    g.minute_counter = 0
    
    print(f"账户ID: {g.accid}")
    print(f"初始资金: {g.money:,.0f}")
    print(f"目标股票: {g.target_stocks}")
    print(f"每次下单数量: {g.order_volume} 股")
    print("=" * 60)


def after_init(C):
    """初始化后处理"""
    print("获取分钟数据...")
    
    data = xtdata.get_market_data_ex(
        stock_list=g.target_stocks,
        period='1m',
        start_time='20250901',
        end_time='20250930',
        dividend_type='front_ratio',
        fill_data=True
    )
    
    if data:
        close_df = get_df_ex(data, "close")
        open_df = get_df_ex(data, "open")
        g.close_df = close_df
        g.open_df = open_df
        
        print(f"数据时间范围: {close_df.index[0]} ~ {close_df.index[-1]}")
        print(f"数据维度: {close_df.shape}")
        print(f"股票数量: {len(close_df.columns)}")
    else:
        print("警告：未获取到数据")
    
    print("初始化完成，准备开始回测")
    print("=" * 60)


def handlebar(C):
    """每分钟执行"""
    g.minute_counter += 1
    
    current_time = timetag_to_datetime(C.get_bar_timetag(C.barpos), "%Y-%m-%d %H:%M:%S")
    current_date = timetag_to_datetime(C.get_bar_timetag(C.barpos), "%Y%m%d")
    
    hold = get_holdings(g.accid, 'stock')
    asset = get_trade_detail_data(g.accid, 'stock', 'account')
    cash = asset[0].m_dAvailable if asset else g.money
    
    print(f"\n[{g.minute_counter}] {current_time}")
    print(f"  持仓数量: {len(hold)}, 可用资金: {cash:,.2f}")
    
    for stock in g.target_stocks:
        try:
            if current_date in g.open_df.index and stock in g.open_df.columns:
                price = g.open_df.loc[current_date, stock]
                
                if pd.notna(price) and price > 0:
                    print(f"  下单 {stock}: 价格={price:.2f}, 数量={g.order_volume}")
                    
                    passorder(
                        23,
                        1102,
                        g.accid,
                        stock,
                        11,
                        float(price),
                        g.order_volume,
                        1,
                        "debug_backtest",
                        "simple_test",
                        C
                    )
                else:
                    print(f"  跳过 {stock}: 无有效价格 (price={price})")
            else:
                print(f"  跳过 {stock}: 数据不存在")
                
        except Exception as e:
            print(f"  错误 {stock}: {e}")
    
    if g.minute_counter % 10 == 0:
        print("\n" + "=" * 60)
        print(f"累计执行 {g.minute_counter} 分钟")
        print(f"当前持仓明细:")
        for stock_code, info in hold.items():
            print(f"  {stock_code}: 持仓={info['持仓数量']}, 成本={info['持仓成本']:.2f}")
        print("=" * 60)


def get_df_ex(data: dict, field: str) -> pd.DataFrame:
    """从get_market_data_ex返回的dict中提取DataFrame"""
    _index = data[list(data.keys())[0]].index.tolist()
    _columns = list(data.keys())
    df = pd.DataFrame(index=_index, columns=_columns)
    for i in _columns:
        df[i] = data[i][field]
    return df


def timetag_to_datetime(timetag, format_str="%Y-%m-%d %H:%M:%S"):
    """将时间戳转换为日期时间字符串"""
    import time
    return time.strftime(format_str, time.localtime(timetag / 1000))


def get_holdings(accid, datatype):
    """获取持仓信息"""
    PositionInfo_dict = {}
    resultlist = get_trade_detail_data(accid, datatype, 'POSITION')
    for obj in resultlist:
        PositionInfo_dict[obj.m_strInstrumentID + "." + obj.m_strExchangeID] = {
            "持仓数量": obj.m_nVolume,
            "持仓成本": obj.m_dOpenPrice,
            "浮动盈亏": obj.m_dFloatProfit,
            "可用余额": obj.m_nCanUseVolume
        }
    return PositionInfo_dict


if __name__ == '__main__':
    import sys
    from xtquant.qmttools import run_strategy_file
    
    param = {
        'stock_code': '000300.SH',
        'period': '1m',
        'start_time': '2025-09-01 09:30:00',
        'end_time': '2025-09-01 15:00:00',
        'trade_mode': 'backtest',
        'quote_mode': 'history',
    }
    
    user_script = sys.argv[0]
    
    print(f"执行脚本: {user_script}")
    print(f"回测参数: {param}")
    print("\n")
    
    result = run_strategy_file(user_script, param=param)
    
    if result:
        print("\n" + "=" * 60)
        print("回测结果:")
        print("=" * 60)
        print(result.get_backtest_index())
        print("\n")
        print(result.get_group_result())
    
    xtdata.run()
