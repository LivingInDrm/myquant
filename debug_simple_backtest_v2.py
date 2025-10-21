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

log_file = open('debug_backtest_log.txt', 'w', encoding='utf-8')

def log(msg):
    print(msg)
    log_file.write(msg + '\n')
    log_file.flush()


def init(C):
    log("=" * 60)
    log("DEBUG BACKTEST - Check Order Execution")
    log("=" * 60)
    
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
    g.order_counter = 0
    
    log(f"Account ID: {g.accid}")
    log(f"Initial Cash: {g.money:,.0f}")
    log(f"Target Stocks: {g.target_stocks}")
    log(f"Order Volume: {g.order_volume} shares per stock")
    log("=" * 60)


def after_init(C):
    log("Fetching minute data...")
    
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
        
        log(f"Data time range: {close_df.index[0]} ~ {close_df.index[-1]}")
        log(f"Data shape: {close_df.shape}")
        log(f"Stock count: {len(close_df.columns)}")
    else:
        log("WARNING: No data fetched")
    
    log("Initialization complete, ready to start backtest")
    log("=" * 60)


def handlebar(C):
    g.minute_counter += 1
    
    current_time = timetag_to_datetime(C.get_bar_timetag(C.barpos), "%Y-%m-%d %H:%M:%S")
    current_date = timetag_to_datetime(C.get_bar_timetag(C.barpos), "%Y%m%d")
    
    hold = get_holdings(g.accid, 'stock')
    asset = get_trade_detail_data(g.accid, 'stock', 'account')
    cash = asset[0].m_dAvailable if asset else g.money
    
    log(f"\n[Minute {g.minute_counter}] {current_time}")
    log(f"  Holdings count: {len(hold)}, Available cash: {cash:,.2f}")
    
    for stock in g.target_stocks:
        try:
            if current_date in g.open_df.index and stock in g.open_df.columns:
                price = g.open_df.loc[current_date, stock]
                
                if pd.notna(price) and price > 0:
                    g.order_counter += 1
                    log(f"  ORDER #{g.order_counter} {stock}: price={price:.2f}, volume={g.order_volume}")
                    
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
                    log(f"  SKIP {stock}: invalid price (price={price})")
            else:
                log(f"  SKIP {stock}: data not found")
                
        except Exception as e:
            log(f"  ERROR {stock}: {e}")
    
    if g.minute_counter % 10 == 0:
        log("\n" + "=" * 60)
        log(f"Summary after {g.minute_counter} minutes")
        log(f"Total orders placed: {g.order_counter}")
        log(f"Current holdings:")
        if hold:
            for stock_code, info in hold.items():
                log(f"  {stock_code}: volume={info['持仓数量']}, cost={info['持仓成本']:.2f}")
        else:
            log("  [EMPTY - NO HOLDINGS]")
        log("=" * 60)


def get_df_ex(data: dict, field: str) -> pd.DataFrame:
    _index = data[list(data.keys())[0]].index.tolist()
    _columns = list(data.keys())
    df = pd.DataFrame(index=_index, columns=_columns)
    for i in _columns:
        df[i] = data[i][field]
    return df


def timetag_to_datetime(timetag, format_str="%Y-%m-%d %H:%M:%S"):
    import time
    return time.strftime(format_str, time.localtime(timetag / 1000))


def get_holdings(accid, datatype):
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
    
    log(f"Running script: {user_script}")
    log(f"Backtest params: {param}")
    log("\n")
    
    result = run_strategy_file(user_script, param=param)
    
    if result:
        log("\n" + "=" * 60)
        log("BACKTEST RESULTS:")
        log("=" * 60)
        log(str(result.get_backtest_index()))
        log("\n")
        log(str(result.get_group_result()))
    
    log_file.close()
    xtdata.run()
