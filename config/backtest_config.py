# coding: utf-8

import os
import yaml


def load_backtest_config(config_path=None):
    """
    Load backtest configuration from YAML file
    
    Args:
        config_path: YAML config file path (default: config/backtest.yaml)
    
    Returns:
        dict: Backtest configuration dictionary
    """
    if config_path is None:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(current_dir, 'backtest.yaml')
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return config


def build_backtest_param(config=None):
    """
    Build QMT backtest param from config
    
    Args:
        config: Backtest config dict (default: load from backtest.yaml)
    
    Returns:
        dict: QMT backtest param in required format
    """
    if config is None:
        config = load_backtest_config()
    
    param = {
        'stock_code': config.get('stock_code', '000001.SZ'),
        'period': config.get('period', '1m'),
        'start_time': config['start_time'],
        'end_time': config['end_time'],
        'trade_mode': config.get('trade_mode', 'backtest'),
        'quote_mode': config.get('quote_mode', 'history'),
        'dividend_type': config.get('dividend_type', 'none'),
        'title': config.get('title', ''),
        'backtest': {}
    }
    
    backtest_cfg = config.get('backtest', {})
    if backtest_cfg:
        param['backtest'] = {
            'asset': backtest_cfg.get('asset', 1000000.0),
            'margin_ratio': backtest_cfg.get('margin_ratio', 0.05),
            'slippage_type': backtest_cfg.get('slippage_type', 2),
            'slippage': backtest_cfg.get('slippage', 0.0),
            'max_vol_rate': backtest_cfg.get('max_vol_rate', 0.0),
            'comsisson_type': backtest_cfg.get('comsisson_type', 0),
            'open_tax': backtest_cfg.get('open_tax', 0.0),
            'close_tax': backtest_cfg.get('close_tax', 0.0),
            'min_commission': backtest_cfg.get('min_commission', 0.0),
            'open_commission': backtest_cfg.get('open_commission', 0.0),
            'close_commission': backtest_cfg.get('close_commission', 0.0),
            'close_today_commission': backtest_cfg.get('close_today_commission', 0.0),
            'benchmark': backtest_cfg.get('benchmark', '000300.SH'),
            'price_type': backtest_cfg.get('price_type', 5),
            'quick_trade': backtest_cfg.get('quick_trade', 0)
        }
    
    return param
