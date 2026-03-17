"""
日志模块

提供统一的日志配置和管理功能，支持文件日志轮转和控制台输出。
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional
from enum import Enum


class LogLevel(Enum):
    """日志级别枚举"""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class Logger:
    """日志管理器
    
    配置和管理日志系统，支持同时输出到文件和控制台。
    使用滚动文件处理器避免日志文件过大。
    """
    
    _loggers: dict = {}
    
    @classmethod
    def setup(cls, name: str, log_file: str, level: str = 'INFO') -> logging.Logger:
        """配置并获取logger对象
        
        Args:
            name: logger名称
            log_file: 日志文件路径
            level: 日志级别，可选值：DEBUG, INFO, WARNING, ERROR, CRITICAL
            
        Returns:
            配置好的logger对象
            
        Raises:
            ValueError: 日志级别无效
        """
        if name in cls._loggers:
            return cls._loggers[name]
        
        logger = logging.getLogger(name)
        logger.setLevel(cls._parse_level(level))
        
        if logger.handlers:
            return logger
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        const_log_path = Path(log_file)
        const_log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(cls._parse_level(level))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        console_handler = logging.StreamHandler()
        console_handler.setLevel(cls._parse_level(level))
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        cls._loggers[name] = logger
        return logger
    
    @classmethod
    def get_logger(cls, name: str) -> Optional[logging.Logger]:
        """获取已配置的logger对象
        
        Args:
            name: logger名称
            
        Returns:
            logger对象，如果不存在则返回None
        """
        return cls._loggers.get(name)
    
    @staticmethod
    def _parse_level(level: str) -> int:
        """将字符串日志级别转换为logging常量
        
        Args:
            level: 日志级别字符串
            
        Returns:
            logging级别常量
            
        Raises:
            ValueError: 日志级别无效
        """
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'WARN': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL,
            'FATAL': logging.CRITICAL
        }
        
        level_upper = level.upper()
        if level_upper not in level_map:
            raise ValueError(f"无效的日志级别: {level}. 有效值为: {', '.join(level_map.keys())}")
        
        return level_map[level_upper]
    
    def __init__(self, name: str, log_file: str, level: str = 'INFO'):
        """初始化日志管理器实例
        
        Args:
            name: logger名称
            log_file: 日志文件路径
            level: 日志级别
        """
        self._logger = self.setup(name, log_file, level)
    
    def debug(self, message: str) -> None:
        """记录DEBUG级别日志
        
        Args:
            message: 日志消息
        """
        self._logger.debug(message)
    
    def info(self, message: str) -> None:
        """记录INFO级别日志
        
        Args:
            message: 日志消息
        """
        self._logger.info(message)
    
    def warning(self, message: str) -> None:
        """记录WARNING级别日志
        
        Args:
            message: 日志消息
        """
        self._logger.warning(message)
    
    def warn(self, message: str) -> None:
        """记录WARNING级别日志（warning的别名）
        
        Args:
            message: 日志消息
        """
        self._logger.warning(message)
    
    def error(self, message: str) -> None:
        """记录ERROR级别日志
        
        Args:
            message: 日志消息
        """
        self._logger.error(message)
    
    def critical(self, message: str) -> None:
        """记录CRITICAL级别日志
        
        Args:
            message: 日志消息
        """
        self._logger.critical(message)
    
    def exception(self, message: str) -> None:
        """记录异常信息（等同于error但会附加堆栈跟踪）
        
        Args:
            message: 日志消息
        """
        self._logger.exception(message)
    
    @property
    def logger(self) -> logging.Logger:
        """获取底层的logger对象"""
        return self._logger


def get_logger(name: str, log_file: str, level: str = 'INFO') -> logging.Logger:
    """便捷函数：获取配置好的logger对象
    
    Args:
        name: logger名称
        log_file: 日志文件路径
        level: 日志级别
        
    Returns:
        配置好的logger对象
    """
    return Logger.setup(name, log_file, level)
