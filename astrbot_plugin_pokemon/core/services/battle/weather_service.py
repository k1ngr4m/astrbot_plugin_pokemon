from typing import TYPE_CHECKING
from .hook_manager import BattleHook

if TYPE_CHECKING:
    from .battle_engine import BattleLogic, BattleLogger

class WeatherService:
    @staticmethod
    def apply_rain(logic: 'BattleLogic', logger_obj: 'BattleLogger'):
        """施加雨天环境"""
        # 1. 清除旧天气钩子 (假设天气互斥)
        logic.field_hooks.unregister("on_damage_calc", "weather_damage_mod")
        
        # 2. 定义雨天逻辑
        def rain_damage_mod(params, attacker, defender, move, logger_obj=None):
            is_real_battle = logger_obj and logger_obj.__class__.__name__ != 'NoOpBattleLogger'
            
            if move.type_name in ['water', '水', 'water']: # covering potential casing issues or mappings
                # 水系威力 x 1.5
                params['power'] = int(params['power'] * 1.5)
                if is_real_battle:
                    logger_obj.log("在雨天中，水属性招式的威力提升了！\n\n")
            elif move.type_name in ['fire', '火', 'fire']:
                # 火系威力 x 0.5
                params['power'] = int(params['power'] * 0.5)
                if is_real_battle:
                    logger_obj.log("受雨天影响，火属性招式的威力减弱了...\n\n")
            return params

        # 3. 注册全局钩子
        # 优先级设为 20
        logic.field_hooks.register("on_damage_calc", BattleHook("weather_damage_mod", 20, rain_damage_mod))
        logic.current_weather = "rain"
        logic.weather_turns = 5 # default 5 turns
        logger_obj.log("开始下雨了！\n\n")
