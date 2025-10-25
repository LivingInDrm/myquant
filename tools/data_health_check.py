#coding: utf-8
import sys
import os
import io

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from xtquant import xtdata
import random


def check_sector_data():
    """检查板块成分股数据"""
    print("\n[1] 板块成分股数据")
    
    try:
        stock_list = xtdata.get_stock_list_in_sector('沪深A股')
        stock_count = len(stock_list)
        
        if 4000 <= stock_count <= 6000:
            status = "[OK]"
        elif stock_count > 0:
            status = "[WARN]"
        else:
            status = "[FAIL]"
        
        print(f"  {status} 沪深A股: {stock_count} 只")
        
        return {
            'status': 'ok' if stock_count >= 4000 else 'warn' if stock_count > 0 else 'fail',
            'count': stock_count,
            'stock_list': stock_list
        }
    except Exception as e:
        print(f"  [FAIL] 获取失败: {e}")
        return {'status': 'fail', 'count': 0, 'stock_list': []}


def check_trading_calendar():
    """检查交易日历数据"""
    print("\n[2] 交易日历数据")
    
    try:
        today = datetime.now()
        three_years_ago = today - timedelta(days=3*365)
        
        start_date = three_years_ago.strftime('%Y%m%d')
        end_date = today.strftime('%Y%m%d')
        
        trading_dates = xtdata.get_trading_dates('SH', start_date, end_date)
        trading_date_count = len(trading_dates)
        
        if 700 <= trading_date_count <= 800:
            status = "[OK]"
        elif trading_date_count > 0:
            status = "[WARN]"
        else:
            status = "[FAIL]"
        
        print(f"  {status} 近3年交易日: {trading_date_count} 天")
        
        if trading_date_count > 0:
            latest_timestamp = trading_dates[-1]
            latest_date = datetime.fromtimestamp(latest_timestamp / 1000)
            days_ago = (today - latest_date).days
            
            if days_ago <= 3:
                date_status = "[OK]"
            elif days_ago <= 7:
                date_status = "[WARN]"
            else:
                date_status = "[FAIL]"
            
            latest_date_str = latest_date.strftime('%Y-%m-%d')
            print(f"  {date_status} 最新交易日: {latest_date_str} ({days_ago}天前)")
            
            return {
                'status': 'ok' if days_ago <= 3 else 'warn',
                'count': trading_date_count,
                'latest_date': latest_date.strftime('%Y%m%d'),
                'days_ago': days_ago,
                'trading_dates': trading_dates
            }
        else:
            return {
                'status': 'fail',
                'count': 0,
                'trading_dates': []
            }
            
    except Exception as e:
        print(f"  [FAIL] 获取失败: {e}")
        return {'status': 'fail', 'count': 0, 'trading_dates': []}


def check_daily_data(stock_list, trading_dates):
    """检查日线数据"""
    print("\n[3] 日线数据 (1d)")
    
    if not stock_list:
        print("  [FAIL] 股票列表为空，跳过检查")
        return {'status': 'fail'}
    
    if not trading_dates or len(trading_dates) == 0:
        print("  [FAIL] 交易日历为空，跳过检查")
        return {'status': 'fail'}
    
    try:
        sample_size = min(50, len(stock_list))
        sample_stocks = random.sample(stock_list, sample_size)
        
        print(f"  [INFO] 抽样 {sample_size} 只股票检查时间范围...")
        
        today = datetime.now()
        five_years_ago = today - timedelta(days=5*365)
        start_date = five_years_ago.strftime('%Y%m%d')
        end_date = today.strftime('%Y%m%d')
        
        data = xtdata.get_market_data_ex(
            stock_list=sample_stocks,
            period='1d',
            start_time=start_date,
            end_time=end_date,
            dividend_type='front_ratio',
            fill_data=False
        )
        
        earliest_date = None
        latest_date = None
        
        for stock, df in data.items():
            if df is not None and len(df) > 0:
                stock_earliest = df.index.min()
                stock_latest = df.index.max()
                
                if earliest_date is None or stock_earliest < earliest_date:
                    earliest_date = stock_earliest
                if latest_date is None or stock_latest > latest_date:
                    latest_date = stock_latest
        
        if earliest_date and latest_date:
            earliest_str = pd.to_datetime(earliest_date).strftime('%Y-%m-%d')
            latest_str = pd.to_datetime(latest_date).strftime('%Y-%m-%d')
            print(f"  时间范围: {earliest_str} ~ {latest_str}")
        else:
            print("  [WARN] 无法确定时间范围")
        
        print(f"  [INFO] 检查全量股票最近1个月覆盖率...")
        one_month_ago = today - timedelta(days=30)
        recent_start = one_month_ago.strftime('%Y%m%d')
        recent_end = today.strftime('%Y%m%d')
        
        batch_size = 500
        total_stocks = len(stock_list)
        success_count = 0
        
        for i in range(0, total_stocks, batch_size):
            batch = stock_list[i:i+batch_size]
            try:
                batch_data = xtdata.get_market_data_ex(
                    stock_list=batch,
                    period='1d',
                    start_time=recent_start,
                    end_time=recent_end,
                    dividend_type='front_ratio',
                    fill_data=False
                )
                
                for stock, df in batch_data.items():
                    if df is not None and len(df) > 0:
                        success_count += 1
                        
            except Exception:
                pass
        
        coverage_rate = (success_count / total_stocks * 100) if total_stocks > 0 else 0
        
        if coverage_rate >= 95:
            status = "[OK]"
        elif coverage_rate >= 80:
            status = "[WARN]"
        else:
            status = "[FAIL]"
        
        print(f"  {status} 覆盖率: {coverage_rate:.1f}% ({success_count}/{total_stocks})")
        
        recent_trading_count = 0
        for timestamp in trading_dates:
            date_obj = datetime.fromtimestamp(timestamp / 1000)
            date_str = date_obj.strftime('%Y%m%d')
            if int(date_str) >= int(recent_start):
                recent_trading_count += 1
        
        expected_days = recent_trading_count
        
        total_missing = 0
        quality_null_count = 0
        quality_total_count = 0
        
        for stock, df in data.items():
            if df is not None and len(df) > 0:
                actual_days = len(df)
                if actual_days < expected_days:
                    total_missing += (expected_days - actual_days)
                
                quality_total_count += df.shape[0] * df.shape[1]
                quality_null_count += df.isnull().sum().sum()
        
        avg_missing = total_missing / len(data) if len(data) > 0 else 0
        null_rate = (quality_null_count / quality_total_count * 100) if quality_total_count > 0 else 0
        
        print(f"  完整性: 平均缺失 {avg_missing:.1f} 天")
        print(f"  质量: 空值率 {null_rate:.2f}%")
        
        return {
            'status': 'ok' if coverage_rate >= 95 else 'warn',
            'earliest_date': earliest_date,
            'latest_date': latest_date,
            'coverage_rate': coverage_rate,
            'avg_missing_days': avg_missing,
            'null_rate': null_rate
        }
        
    except Exception as e:
        print(f"  [FAIL] 检查失败: {e}")
        return {'status': 'fail'}


def check_minute_data(stock_list, trading_dates, period='1m'):
    """检查分钟线数据"""
    print(f"\n[{'4' if period == '1m' else '5'}] 分钟线数据 ({period})")
    
    if not stock_list:
        print("  [FAIL] 股票列表为空，跳过检查")
        return {'status': 'fail'}
    
    if not trading_dates or len(trading_dates) == 0:
        print("  [FAIL] 交易日历为空，跳过检查")
        return {'status': 'fail'}
    
    try:
        sample_size = min(50, len(stock_list))
        sample_stocks = random.sample(stock_list, sample_size)
        
        print(f"  [INFO] 抽样 {sample_size} 只股票检查时间范围...")
        
        today = datetime.now()
        three_years_ago = today - timedelta(days=3*365)
        start_date = three_years_ago.strftime('%Y%m%d')
        end_date = today.strftime('%Y%m%d')
        
        data = xtdata.get_market_data_ex(
            stock_list=sample_stocks,
            period=period,
            start_time=start_date,
            end_time=end_date,
            dividend_type='front_ratio',
            fill_data=False
        )
        
        earliest_date = None
        latest_date = None
        stocks_with_data = 0
        
        for stock, df in data.items():
            if df is not None and len(df) > 0:
                stocks_with_data += 1
                stock_earliest = df.index.min()
                stock_latest = df.index.max()
                
                if earliest_date is None or stock_earliest < earliest_date:
                    earliest_date = stock_earliest
                if latest_date is None or stock_latest > latest_date:
                    latest_date = stock_latest
        
        if earliest_date and latest_date:
            earliest_str = pd.to_datetime(earliest_date).strftime('%Y-%m-%d')
            latest_str = pd.to_datetime(latest_date).strftime('%Y-%m-%d')
            print(f"  时间范围: {earliest_str} ~ {latest_str}")
            
            latest_date_obj = pd.to_datetime(latest_date)
            latest_date_int = int(latest_date_obj.strftime('%Y%m%d'))
            
            check_days = []
            for timestamp in reversed(trading_dates):
                date_obj = datetime.fromtimestamp(timestamp / 1000)
                date_str = date_obj.strftime('%Y%m%d')
                date_int = int(date_str)
                
                if date_int <= latest_date_int:
                    check_days.append(date_str)
                    if len(check_days) >= 3:
                        break
            
            check_days.reverse()
            
            if len(check_days) == 0:
                print("  [WARN] 数据范围内无交易日可检查")
                return {
                    'status': 'warn',
                    'earliest_date': earliest_date,
                    'latest_date': latest_date,
                    'coverage_rate': 0,
                    'avg_bars': 0
                }
            
            print(f"  [INFO] 在数据范围内检查最新{len(check_days)}个交易日覆盖率...")
        else:
            print("  [WARN] 无法确定时间范围（无数据）")
            return {
                'status': 'fail',
                'coverage_rate': 0
            }
        
        success_count = 0
        total_bars = 0
        expected_bars_per_day = 240 if period == '1m' else 48
        
        data_matrix = {}
        for stock in sample_stocks:
            data_matrix[stock] = {}
            for date in check_days:
                data_matrix[stock][date] = {'has_data': False, 'bars': 0}
        
        for date in check_days:
            try:
                batch_data = xtdata.get_market_data_ex(
                    stock_list=sample_stocks,
                    period=period,
                    start_time=date,
                    end_time=date,
                    dividend_type='front_ratio',
                    fill_data=False
                )
                
                for stock, df in batch_data.items():
                    if df is not None and len(df) > 0:
                        success_count += 1
                        total_bars += len(df)
                        data_matrix[stock][date]['has_data'] = True
                        data_matrix[stock][date]['bars'] = len(df)
                        
            except Exception:
                pass
        
        coverage_rate = (success_count / (sample_size * len(check_days)) * 100) if sample_size > 0 and len(check_days) > 0 else 0
        avg_bars = total_bars / success_count if success_count > 0 else 0
        
        if coverage_rate >= 80:
            status = "[OK]"
        elif coverage_rate >= 50:
            status = "[WARN]"
        else:
            status = "[FAIL]"
        
        print(f"  {status} 覆盖率: {coverage_rate:.1f}% ({success_count}/{sample_size * len(check_days)})")
        
        if success_count > 0:
            print(f"  完整性: 平均每天 {avg_bars:.0f} 根K线 (预期{expected_bars_per_day}根)")
        
        missing_details = []
        for stock in sample_stocks:
            missing_dates = []
            for date in check_days:
                if not data_matrix[stock][date]['has_data']:
                    missing_dates.append(date)
            if missing_dates:
                missing_details.append({
                    'stock': stock,
                    'dates': missing_dates
                })
        
        if missing_details:
            print(f"  [INFO] 缺失明细: {len(missing_details)} 只股票存在数据缺失")
            
            for item in missing_details:
                stock = item['stock']
                dates = item['dates']
                dates_str = ', '.join([d[:4]+'-'+d[4:6]+'-'+d[6:] for d in dates])
                print(f"    - {stock}: {dates_str}")
        
        return {
            'status': 'ok' if coverage_rate >= 80 else 'warn' if coverage_rate >= 50 else 'fail',
            'earliest_date': earliest_date,
            'latest_date': latest_date,
            'coverage_rate': coverage_rate,
            'avg_bars': avg_bars
        }
        
    except Exception as e:
        print(f"  [FAIL] 检查失败: {e}")
        return {'status': 'fail'}


def check_instrument_info(stock_list):
    """检查股票基础信息"""
    print("\n[6] 股票基础信息")
    
    if not stock_list:
        print("  [FAIL] 股票列表为空，跳过检查")
        return {'status': 'fail'}
    
    try:
        print(f"  [INFO] 检查 {len(stock_list)} 只股票...")
        
        success_count = 0
        missing_opendate_count = 0
        
        batch_size = 100
        for i in range(0, len(stock_list), batch_size):
            batch = stock_list[i:i+batch_size]
            
            for stock in batch:
                try:
                    detail = xtdata.get_instrument_detail(stock)
                    if detail:
                        success_count += 1
                        opendate = detail.get('OpenDate', '')
                        if not opendate or opendate == '19700101':
                            missing_opendate_count += 1
                except Exception:
                    pass
        
        coverage_rate = (success_count / len(stock_list) * 100) if len(stock_list) > 0 else 0
        
        if coverage_rate >= 95:
            status = "[OK]"
        elif coverage_rate >= 80:
            status = "[WARN]"
        else:
            status = "[FAIL]"
        
        print(f"  {status} 覆盖率: {coverage_rate:.1f}% ({success_count}/{len(stock_list)})")
        print(f"  质量: 缺失上市日期 {missing_opendate_count} 只")
        
        return {
            'status': 'ok' if coverage_rate >= 95 else 'warn',
            'coverage_rate': coverage_rate,
            'missing_opendate': missing_opendate_count
        }
        
    except Exception as e:
        print(f"  [FAIL] 检查失败: {e}")
        return {'status': 'fail'}


def print_summary(results):
    """打印总结报告"""
    print("\n========== 总体评估 ==========")
    
    status_counts = {
        'ok': 0,
        'warn': 0,
        'fail': 0
    }
    
    for key, result in results.items():
        status = result.get('status', 'fail')
        if status in status_counts:
            status_counts[status] += 1
    
    total = sum(status_counts.values())
    
    if status_counts['fail'] > 0:
        health = "较差"
    elif status_counts['warn'] > total / 2:
        health = "一般"
    elif status_counts['warn'] > 0:
        health = "良好"
    else:
        health = "优秀"
    
    print(f"健康度: {health}")
    print(f"检查项: {status_counts['ok']}项正常, {status_counts['warn']}项警告, {status_counts['fail']}项失败")
    
    suggestions = []
    
    if results.get('daily', {}).get('coverage_rate', 0) < 95:
        suggestions.append("日线数据覆盖不足，建议补充下载")
    
    if results.get('minute_1m', {}).get('coverage_rate', 0) < 50:
        suggestions.append("1分钟线数据覆盖不足，建议下载")
    
    if results.get('minute_5m', {}).get('coverage_rate', 0) < 50:
        suggestions.append("5分钟线数据覆盖不足，建议下载")
    
    if results.get('instrument', {}).get('missing_opendate', 0) > 10:
        suggestions.append("部分股票缺失上市日期信息")
    
    if results.get('calendar', {}).get('days_ago', 999) > 3:
        suggestions.append("交易日历数据可能未及时更新")
    
    if suggestions:
        print("建议: " + "; ".join(suggestions))
    else:
        print("建议: 数据状态良好，无需特别操作")


def main():
    """主函数"""
    print("========== QMT数据健康度报告 ==========")
    print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        data_dir = xtdata.get_data_dir()
        print(f"数据目录: {data_dir}")
    except Exception:
        print("数据目录: 无法获取")
    
    results = {}
    
    sector_result = check_sector_data()
    results['sector'] = sector_result
    stock_list = sector_result.get('stock_list', [])
    
    calendar_result = check_trading_calendar()
    results['calendar'] = calendar_result
    trading_dates = calendar_result.get('trading_dates', [])
    
    daily_result = check_daily_data(stock_list, trading_dates)
    results['daily'] = daily_result
    
    minute_1m_result = check_minute_data(stock_list, trading_dates, period='1m')
    results['minute_1m'] = minute_1m_result
    
    minute_5m_result = check_minute_data(stock_list, trading_dates, period='5m')
    results['minute_5m'] = minute_5m_result
    
    instrument_result = check_instrument_info(stock_list)
    results['instrument'] = instrument_result
    
    print_summary(results)
    
    print("\n检查完成!")


if __name__ == '__main__':
    main()
