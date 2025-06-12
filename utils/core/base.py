"""
Base utilities module for CONTRO Bot
Provides common functionality shared across all modules
"""

import logging
import asyncio
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import json
import os
from pathlib import Path

class BaseModule:
    """Base class for all bot modules"""
    
    def __init__(self, name: str, config_path: str = None):
        self.name = name
        self.logger = logging.getLogger(f'contro.{name}')
        self.config_path = config_path
        self._config = {}
        self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load module configuration"""
        if not self.config_path or not os.path.exists(self.config_path):
            return {}
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
            self.logger.info(f"Configuration loaded for {self.name}")
        except Exception as e:
            self.logger.error(f"Failed to load config for {self.name}: {e}")
            self._config = {}
        
        return self._config
    
    def save_config(self) -> bool:
        """Save module configuration"""
        if not self.config_path:
            return False
        
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Configuration saved for {self.name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save config for {self.name}: {e}")
            return False
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self._config.get(key, default)
    
    def set_config(self, key: str, value: Any) -> None:
        """Set configuration value"""
        self._config[key] = value
    
    async def initialize(self) -> bool:
        """Initialize the module (override in subclasses)"""
        self.logger.info(f"Initializing {self.name}")
        return True
    
    async def cleanup(self) -> bool:
        """Cleanup the module (override in subclasses)"""
        self.logger.info(f"Cleaning up {self.name}")
        return True


class DataManager:
    """Centralized data management"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger('contro.data_manager')
    
    def get_file_path(self, filename: str) -> Path:
        """Get full path for a data file"""
        return self.data_dir / filename
    
    def load_json(self, filename: str, default: Any = None) -> Any:
        """Load JSON data from file"""
        file_path = self.get_file_path(filename)
        
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load {filename}: {e}")
        
        return default if default is not None else {}
    
    def save_json(self, filename: str, data: Any) -> bool:
        """Save data to JSON file"""
        file_path = self.get_file_path(filename)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            self.logger.error(f"Failed to save {filename}: {e}")
            return False
    
    def backup_file(self, filename: str) -> bool:
        """Create backup of a file"""
        file_path = self.get_file_path(filename)
        
        if not file_path.exists():
            return False
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = file_path.with_suffix(f".{timestamp}.backup")
        
        try:
            import shutil
            shutil.copy2(file_path, backup_path)
            self.logger.info(f"Backup created: {backup_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to backup {filename}: {e}")
            return False


class EventEmitter:
    """Simple event system for module communication"""
    
    def __init__(self):
        self._listeners: Dict[str, List[callable]] = {}
        self.logger = logging.getLogger('contro.events')
    
    def on(self, event: str, callback: callable) -> None:
        """Register event listener"""
        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append(callback)
    
    def off(self, event: str, callback: callable) -> None:
        """Remove event listener"""
        if event in self._listeners:
            try:
                self._listeners[event].remove(callback)
            except ValueError:
                pass
    
    async def emit(self, event: str, *args, **kwargs) -> None:
        """Emit event to all listeners"""
        if event not in self._listeners:
            return
        
        for callback in self._listeners[event]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(*args, **kwargs)
                else:
                    callback(*args, **kwargs)
            except Exception as e:
                self.logger.error(f"Error in event listener for {event}: {e}")


class ModuleRegistry:
    """Registry for all bot modules"""
    
    def __init__(self):
        self._modules: Dict[str, BaseModule] = {}
        self.events = EventEmitter()
        self.data_manager = DataManager()
        self.logger = logging.getLogger('contro.registry')
    
    def register(self, module: BaseModule) -> None:
        """Register a module"""
        self._modules[module.name] = module
        self.logger.info(f"Registered module: {module.name}")
    
    def unregister(self, name: str) -> None:
        """Unregister a module"""
        if name in self._modules:
            del self._modules[name]
            self.logger.info(f"Unregistered module: {name}")
    
    def get(self, name: str) -> Optional[BaseModule]:
        """Get a module by name"""
        return self._modules.get(name)
    
    def get_all(self) -> Dict[str, BaseModule]:
        """Get all registered modules"""
        return self._modules.copy()
    
    async def initialize_all(self) -> None:
        """Initialize all modules"""
        for module in self._modules.values():
            try:
                await module.initialize()
            except Exception as e:
                self.logger.error(f"Failed to initialize {module.name}: {e}")
    
    async def cleanup_all(self) -> None:
        """Cleanup all modules"""
        for module in self._modules.values():
            try:
                await module.cleanup()
            except Exception as e:
                self.logger.error(f"Failed to cleanup {module.name}: {e}")


# Global registry instance
registry = ModuleRegistry()


class AsyncCache:
    """Simple async cache implementation"""
    
    def __init__(self, default_ttl: int = 300):  # 5 minutes default
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
        self.logger = logging.getLogger('contro.cache')
    
    def _is_expired(self, item: Dict[str, Any]) -> bool:
        """Check if cache item is expired"""
        if 'expires_at' not in item:
            return False
        return datetime.now().timestamp() > item['expires_at']
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key not in self._cache:
            return None
        
        item = self._cache[key]
        if self._is_expired(item):
            del self._cache[key]
            return None
        
        return item['value']
    
    async def set(self, key: str, value: Any, ttl: int = None) -> None:
        """Set value in cache"""
        ttl = ttl or self.default_ttl
        expires_at = datetime.now().timestamp() + ttl
        
        self._cache[key] = {
            'value': value,
            'expires_at': expires_at,
            'created_at': datetime.now().timestamp()
        }
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    async def clear(self) -> None:
        """Clear all cache"""
        self._cache.clear()
    
    async def cleanup_expired(self) -> int:
        """Remove expired items and return count"""
        expired_keys = [
            key for key, item in self._cache.items()
            if self._is_expired(item)
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        return len(expired_keys)


# Global cache instance
cache = AsyncCache()


def get_module_logger(module_name: str) -> logging.Logger:
    """Get a logger for a specific module"""
    return logging.getLogger(f'contro.{module_name}')


def ensure_directory(path: Union[str, Path]) -> Path:
    """Ensure a directory exists"""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_json_load(file_path: Union[str, Path], default: Any = None) -> Any:
    """Safely load JSON file with fallback"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}


def safe_json_save(file_path: Union[str, Path], data: Any) -> bool:
    """Safely save JSON file"""
    try:
        ensure_directory(Path(file_path).parent)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False
