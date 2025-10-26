#coding: utf-8

from .mod import XTSourceMod


def load_mod():
    """
    RQAlpha调用此函数加载mod
    
    Returns:
        XTSourceMod实例
    """
    return XTSourceMod()


__all__ = ['load_mod', 'XTSourceMod']
