#coding: utf-8
"""
交易日志模块
提供精简且结构化的交易日志记录功能
"""

def format_amount(amount):
    """格式化金额为万元"""
    return f"{amount / 10000:.1f}万"

def format_price(price):
    """格式化价格保留2位小数"""
    return f"{price:.2f}"

def format_pct(pct):
    """格式化百分比保留1位小数"""
    sign = '+' if pct >= 0 else ''
    return f"{sign}{pct:.1f}%"

def format_score_detail(score_detail):
    """格式化评分明细"""
    if not score_detail:
        return ""
    return f"MA{score_detail.get('ma_points', 0)}+MAX{score_detail.get('max_points', 0)}+排列{score_detail.get('arrangement_points', 0)}+量比{score_detail.get('volume_points', 0)}"

def log_buy_funnel(logger, timestamp, funnel_stats, buy_count, cash):
    """
    记录买入筛选漏斗日志
    
    Args:
        logger: 日志对象
        timestamp: 时间戳 (格式: YYYYMMDD HH:MM)
        funnel_stats: 漏斗统计数据 {'total': X, 'cond1': Y, 'cond2': Z, 'score': A, 'listing': B}
        buy_count: 最终买入数量
        cash: 可用资金
    """
    total = funnel_stats.get('total', 0)
    cond1 = funnel_stats.get('cond1', 0)
    cond2 = funnel_stats.get('cond2', 0)
    score = funnel_stats.get('score', 0)
    listing = funnel_stats.get('listing', 0)
    min_score = funnel_stats.get('min_score', 0)
    
    logger.info(
        f"[{timestamp}] 筛选漏斗: 全市场->条件1({cond1})->条件2({cond2})->评分>{min_score}({score})->上市天数({listing}) | "
        f"买入{buy_count}只 资金{format_amount(cash)}"
    )

def log_buy_trade(logger, timestamp, stock_code, price, volume, amount, fee, score, score_detail, limit_prices=None):
    """
    记录买入交易日志
    
    Args:
        logger: 日志对象
        timestamp: 时间戳 (格式: YYYYMMDD HH:MM)
        stock_code: 股票代码
        price: 成交价格
        volume: 成交数量
        amount: 成交金额
        fee: 手续费
        score: 总评分
        score_detail: 评分明细 {'ma_points': 5, 'max_points': 5, ...}
        limit_prices: 涨跌停价格 {'up_stop': 10.50, 'down_stop': 8.50} (可选)
    """
    detail_str = format_score_detail(score_detail)
    
    limit_str = ""
    if limit_prices:
        up_stop = limit_prices.get('up_stop')
        down_stop = limit_prices.get('down_stop')
        if up_stop is not None and down_stop is not None:
            limit_str = f" 涨停{format_price(up_stop)} 跌停{format_price(down_stop)}"
    
    logger.info(
        f"[{timestamp}] 买入 {stock_code} "
        f"价格{format_price(price)} 数量{volume}股 金额{format_amount(amount)} 费用{fee:.1f}{limit_str} | "
        f"评分{score}({detail_str})"
    )

def log_sell_trade(logger, timestamp, stock_code, buy_info, sell_info, reason_detail, score_change):
    """
    记录卖出交易日志
    
    Args:
        logger: 日志对象
        timestamp: 时间戳 (格式: YYYYMMDD HH:MM)
        stock_code: 股票代码
        buy_info: 买入信息 {'price': 12.50, 'volume': 19600, 'date': '...'}
        sell_info: 卖出信息 {'price': 11.25, 'volume': 19600, 'fee': 73.5}
        reason_detail: 退出原因明细 {'type': 'STOP_LOSS', 'pct': -10.2, 'days': 3}
        score_change: 评分变化 {'old_score': 18, 'old_detail': {...}, 'new_score': 7, 'new_detail': {...}}
    """
    buy_price = buy_info['price']
    sell_price = sell_info['price']
    volume = sell_info['volume']
    fee = sell_info.get('fee', 0)
    
    profit_pct = (sell_price - buy_price) / buy_price * 100
    profit_amount = (sell_price - buy_price) * volume - fee
    
    reason_type = reason_detail['type']
    days = reason_detail.get('days', 0)
    
    if reason_type == 'STOP_LOSS':
        reason_str = f"止损 {format_pct(reason_detail['pct'])}"
    elif reason_type == 'TAKE_PROFIT':
        reason_str = f"止盈 {format_pct(reason_detail['pct'])}"
    elif reason_type == 'SCORE_DROP':
        old_score = reason_detail['old_score']
        new_score = reason_detail['new_score']
        reason_str = f"评分{old_score}->{new_score}"
    elif reason_type == 'MAX_DAYS':
        limit = reason_detail['limit']
        reason_str = f"持有{days}/{limit}天"
    else:
        reason_str = reason_type
    
    old_score = score_change['old_score']
    new_score = score_change['new_score']
    old_detail_str = format_score_detail(score_change.get('old_detail'))
    new_detail_str = format_score_detail(score_change.get('new_detail'))
    
    profit_str = "盈" if profit_amount >= 0 else "亏"
    
    logger.info(
        f"[{timestamp}] 卖出 {stock_code} [{reason_str}] "
        f"持有{days}天 买入{format_price(buy_price)}->卖出{format_price(sell_price)} "
        f"{profit_str}{profit_amount:+.0f}元({format_pct(profit_pct)}) | "
        f"评分{old_score}({old_detail_str})->{new_score}({new_detail_str})"
    )

def log_daily_position_snapshot(logger, date, account_summary, position_details):
    """
    记录每日持仓快照
    
    Args:
        logger: 日志对象
        date: 日期 (格式: YYYY-MM-DD)
        account_summary: 账户汇总 {'total_assets': X, 'position_count': Y, 'cash': Z, 'daily_pnl': A, 'daily_pnl_pct': B}
        position_details: 持仓明细列表 [{'stock_code': ..., 'days': ..., 'cost': ..., 'price': ..., 'volume': ..., 'amount': ..., 'pnl_pct': ..., 'score': ..., 'score_detail': ...}, ...]
    """
    total_assets = account_summary['total_assets']
    position_count = account_summary['position_count']
    cash = account_summary['cash']
    daily_pnl = account_summary.get('daily_pnl', 0)
    daily_pnl_pct = account_summary.get('daily_pnl_pct', 0)
    
    logger.info(
        f"[收盘] {date} 总资产{format_amount(total_assets)} 持仓{position_count}只 "
        f"现金{format_amount(cash)} 当日盈亏{daily_pnl:+.0f}元({format_pct(daily_pnl_pct)})"
    )
    
    for pos in position_details:
        stock_code = pos['stock_code']
        days = pos['days']
        cost = pos['cost']
        price = pos['price']
        volume = pos.get('volume', 0)
        amount = pos.get('amount', 0)
        pnl_pct = pos['pnl_pct']
        score = pos['score']
        score_detail = pos.get('score_detail', {})
        
        detail_str = format_score_detail(score_detail)
        
        logger.info(
            f"  |- {stock_code} 持有{days}天 数量{volume}股 金额{format_amount(amount)} "
            f"成本{format_price(cost)} 现价{format_price(price)} 浮{format_pct(pnl_pct)} 评分{score}({detail_str})"
        )
