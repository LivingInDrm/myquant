#coding: utf-8
import logging
import sys
import io
from datetime import datetime
import os


def setup_utf8_output():
    """
    修复Windows控制台中文乱码问题
    强制stdout使用UTF-8编码，避免GBK编码导致的乱码
    """
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def get_logger(name, log_file=None, level=logging.INFO):
    """
    创建并返回配置好的logger实例
    
    Args:
        name: logger名称，会显示在日志输出中
        log_file: 日志文件路径，如果为None则不输出到文件
        level: 日志级别，默认INFO
    
    Returns:
        配置好的logger实例
    """
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    logger.propagate = False
    
    return logger


def get_log_filename(prefix='backtest'):
    """
    生成带时间戳的日志文件名
    
    Args:
        prefix: 文件名前缀
    
    Returns:
        格式化的日志文件路径: logs/{prefix}_YYYYMMDD_HHMMSS.log
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f'logs/{prefix}_{timestamp}.log'
