"""
配置管理模块

提供统一的配置文件读取和管理功能，支持类型安全的配置访问。
"""

import json
from pathlib import Path
from typing import Any, Optional, Dict


class ConfigManager:
    """配置管理器
    
    从JSON配置文件中加载配置，并提供类型安全的访问方法。
    支持配置热重载和默认值处理。
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化配置管理器
        
        Args:
            config_path: 配置文件路径，如果为None则不加载配置
        """
        self._config_path: Optional[str] = config_path
        self._config: Dict[str, Any] = {}
        
        if config_path:
            self.load(config_path)
    
    def load(self, config_path: str) -> None:
        """从JSON文件加载配置
        
        Args:
            config_path: JSON配置文件的路径
            
        Raises:
            FileNotFoundError: 配置文件不存在
            json.JSONDecodeError: 配置文件格式错误
        """
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            self._config = json.load(f)
        self._config_path = config_path
    
    def reload(self) -> None:
        """重新加载配置文件
        
        如果配置管理器初始化时没有指定config_path，此操作会抛出ValueError。
        
        Raises:
            ValueError: 没有配置文件路径
        """
        if not self._config_path:
            raise ValueError("无法重新加载配置：未设置配置文件路径")
        self.load(self._config_path)
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值
        
        Args:
            key: 配置键，支持点号分隔的多级键（如'section.key'）
            default: 默认值，当键不存在时返回
            
        Returns:
            配置值或默认值
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """获取布尔类型配置值
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            布尔值
        """
        value = self.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        if isinstance(value, (int, float)):
            return bool(value)
        return default
    
    def get_int(self, key: str, default: int = 0) -> int:
        """获取整数类型配置值
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            整数值
        """
        try:
            value = self.get(key, default)
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def get_float(self, key: str, default: float = 0.0) -> float:
        """获取浮点数类型配置值
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            浮点数值
        """
        try:
            value = self.get(key, default)
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def get_str(self, key: str, default: str = "") -> str:
        """获取字符串类型配置值
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            字符串值
        """
        value = self.get(key, default)
        return str(value) if value is not None else default
    
    def get_list(self, key: str, default: Optional[list] = None) -> list:
        """获取列表类型配置值
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            列表值
        """
        if default is None:
            default = []
        
        value = self.get(key, default)
        if isinstance(value, list):
            return value
        return default
    
    def get_dict(self, key: str, default: Optional[dict] = None) -> dict:
        """获取字典类型配置值
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            字典值
        """
        if default is None:
            default = {}
        
        value = self.get(key, default)
        if isinstance(value, dict):
            return value
        return default
    
    def set(self, key: str, value: Any) -> None:
        """设置配置值（仅在内存中修改）
        
        Args:
            key: 配置键，支持点号分隔的多级键
            value: 配置值
        """
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            if k not in config or not isinstance(config[k], dict):
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def save(self, config_path: Optional[str] = None) -> None:
        """保存配置到JSON文件
        
        Args:
            config_path: 目标文件路径，如果为None则使用原路径
        """
        target_path = config_path or self._config_path
        if not target_path:
            raise ValueError("无法保存配置：未设置目标路径")
        
        target_file = Path(target_path)
        target_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(target_file, 'w', encoding='utf-8') as f:
            json.dump(self._config, f, indent=4, ensure_ascii=False)
    
    @property
    def config(self) -> Dict[str, Any]:
        """获取完整的配置字典（只读）"""
        return self._config.copy()
