"""
电源管理模块 - 防止系统睡眠
"""
import ctypes
import platform
from typing import Optional

# Windows API 常量
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

class PowerManager:
    """电源管理器 - 控制系统睡眠状态"""

    def __init__(self):
        self._is_enabled = False
        self._platform = platform.system()

    def enable_prevent_sleep(self) -> bool:
        """
        启用防睡眠模式

        Returns:
            bool: True 成功启用，False 已启用或失败
        """
        if self._is_enabled:
            return False

        try:
            if self._platform == "Windows":
                # Windows: 使用 SetThreadExecutionState
                # ES_CONTINUOUS | ES_SYSTEM_REQUIRED: 防止系统睡眠
                # 不包含 ES_DISPLAY_REQUIRED: 允许显示器关闭
                ctypes.windll.kernel32.SetThreadExecutionState(
                    ES_CONTINUOUS | ES_SYSTEM_REQUIRED
                )
                self._is_enabled = True
                print("[电源管理] 已启用防睡眠模式（允许显示器关闭）", flush=True)
                return True
            else:
                # macOS/Linux: 暂不支持，只记录日志
                print(f"[电源管理] 当前平台 ({self._platform}) 暂不支持防睡眠功能", flush=True)
                return False
        except Exception as e:
            print(f"[电源管理] 启用防睡眠失败: {str(e)}", flush=True)
            return False

    def disable_prevent_sleep(self) -> bool:
        """
        禁用防睡眠模式，恢复系统默认设置

        Returns:
            bool: True 成功禁用，False 未启用或失败
        """
        if not self._is_enabled:
            return False

        try:
            if self._platform == "Windows":
                # 恢复系统默认电源设置
                ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
                self._is_enabled = False
                print("[电源管理] 已恢复正常电源设置", flush=True)
                return True
            else:
                return False
        except Exception as e:
            print(f"[电源管理] 禁用防睡眠失败: {str(e)}", flush=True)
            return False

    @property
    def is_enabled(self) -> bool:
        """检查是否已启用防睡眠"""
        return self._is_enabled

# 全局单例
_power_manager: Optional[PowerManager] = None

def get_power_manager() -> PowerManager:
    """获取全局电源管理器单例"""
    global _power_manager
    if _power_manager is None:
        _power_manager = PowerManager()
    return _power_manager

def prevent_sleep_enable() -> bool:
    """快捷函数：启用防睡眠"""
    return get_power_manager().enable_prevent_sleep()

def prevent_sleep_disable() -> bool:
    """快捷函数：禁用防睡眠"""
    return get_power_manager().disable_prevent_sleep()
