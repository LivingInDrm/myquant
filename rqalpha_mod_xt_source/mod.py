#coding: utf-8

from rqalpha.interface import AbstractMod
from rqalpha.utils.logger import system_log

from .data_source import XTDataSource


class XTSourceMod(AbstractMod):
    """
    QMT数据源Mod
    
    将RQAlpha的分钟级行情数据切换到QMT，其他数据仍使用RQAlpha默认数据源
    """
    
    def __init__(self):
        self._data_source = None
    
    def start_up(self, env, mod_config):
        """
        Mod启动时调用
        
        Args:
            env: RQAlpha环境对象
            mod_config: Mod配置
        """
        try:
            system_log.info("[XTSourceMod] 正在启动QMT数据源模块...")
            
            data_bundle_path = env.config.base.data_bundle_path
            
            custom_future_info = {}
            
            self._data_source = XTDataSource(
                path=data_bundle_path,
                custom_future_info=custom_future_info
            )
            
            env.set_data_source(self._data_source)
            
            system_log.info("[XTSourceMod] QMT数据源模块启动成功")
            system_log.info("[XTSourceMod] 分钟级数据将从QMT获取，其他数据使用RQAlpha默认数据源")
            
        except Exception as e:
            system_log.error(f"[XTSourceMod] 启动失败: {e}")
            raise
    
    def tear_down(self, code, exception=None):
        """
        Mod关闭时调用
        
        Args:
            code: 退出码
            exception: 异常对象
        """
        system_log.info("[XTSourceMod] QMT数据源模块已关闭")
