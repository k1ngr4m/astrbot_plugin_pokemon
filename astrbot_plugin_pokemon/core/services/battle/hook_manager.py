from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field
import bisect

@dataclass
class BattleHook:
    """钩子基础定义"""
    name: str  # 钩子标识符，例如 "burn_effect"
    priority: int = 10  # 优先级，数值越小越先执行
    callback: Callable = None  # 触发时的回调函数
    persistent: bool = True  # 是否持久化，False 则触发一次后移除

class HookManager:
    """钩子管理器：负责注册、注销和触发事件"""
    def __init__(self):
        # 存储格式：{ "event_name": [BattleHook, ...] }
        self._hooks: Dict[str, List[BattleHook]] = {
            "before_move": [],      # 招式发动前 (可取消行动)
            "on_stat_calc": [],     # 能力值计算 (修正攻击/速度等)
            "on_damage_calc": [],   # 伤害计算中 (属性修正、威力修正)
            "after_damage": [],     # 造成伤害后 (反伤、吸血)
            "turn_end": [],         # 回合结束时 (中毒扣血、道具回复)
            "on_faint": []          # 濒死时 (气势披带判断)
        }

    def register(self, event: str, hook: BattleHook):
        """注册一个钩子，按优先级排序"""
        if event not in self._hooks:
            self._hooks[event] = []
        # 使用二分法保持列表按 priority 排序
        bisect.insort(self._hooks[event], hook, key=lambda x: x.priority)

    def unregister(self, event: str, hook_name: str):
        """根据名称注销钩子"""
        if event in self._hooks:
            self._hooks[event] = [h for h in self._hooks[event] if h.name != hook_name]

    def trigger_action(self, event: str, *args, **kwargs) -> bool:
        """
        触发动作型钩子：任何一个钩子返回 False，则整个动作取消
        常用于 before_move (如麻痹、睡眠判定)
        """
        for hook in list(self._hooks.get(event, [])): # Iterate over a copy to allow modification during iteration if needed
            can_continue = hook.callback(*args, **kwargs)
            if not hook.persistent:
                self.unregister(event, hook.name)
            if can_continue is False: # Explicit check for False
                return False
        return True

    def trigger_value(self, event: str, value: Any, *args, **kwargs) -> Any:
        """
        触发数值型钩子：依次修正传入的 value 并返回最终值
        常用于 on_stat_calc 或 on_damage_calc
        """
        current_value = value
        for hook in list(self._hooks.get(event, [])):
            current_value = hook.callback(current_value, *args, **kwargs)
            if not hook.persistent:
                self.unregister(event, hook.name)
        return current_value

    def trigger_event(self, event: str, *args, **kwargs):
        """
        触发事件型钩子：仅执行副作用，不返回值
        常用于 turn_end (如中毒、烧伤扣血)
        """
        for hook in list(self._hooks.get(event, [])):
            hook.callback(*args, **kwargs)
            if not hook.persistent:
                self.unregister(event, hook.name)
