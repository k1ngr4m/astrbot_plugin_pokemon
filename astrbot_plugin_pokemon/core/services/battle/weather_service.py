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

    @staticmethod
    def apply_sandstorm(logic: 'BattleLogic', logger_obj: 'BattleLogger'):
        """施加沙暴环境"""
        # 1. 清理旧天气钩子
        logic._clear_weather(logger_obj)
        
        # 2. 定义特防加成逻辑 (仅限岩石系)
        def sandstorm_stat_mod(stats, state):
            # 检查宝可梦属性是否包含岩石系
            types = [t.lower() for t in state.context.types]
            if 'rock' in types or '岩石' in types:
                # 特防提升 1.5 倍
                stats.sp_defense = int(stats.sp_defense * 1.5)
            return stats

        # 3. 定义残余伤害逻辑
        def sandstorm_residual_dmg(state, opponent, logger_obj):
            types = [t.lower() for t in state.context.types]
            immune_types = {'rock', 'ground', 'steel', '岩石', '地面', '钢'}
            
            # 只有非岩、地、钢系的宝可梦会受到伤害
            if not any(t in immune_types for t in types):
                max_hp = state.context.pokemon.stats.hp
                dmg = max(1, max_hp // 16)
                state.current_hp -= dmg
                logger_obj.log(f"沙暴正肆虐！{state.context.pokemon.name} 受到伤害！\n\n")
        
        # 4. 注册全局钩子
        # 注册数值修正钩子
        logic.field_hooks.register("on_stat_calc", BattleHook("weather_stat_mod", 10, sandstorm_stat_mod))
        # 注册回合结束钩子
        logic.field_hooks.register("turn_end", BattleHook("weather_residual_dmg", 10, sandstorm_residual_dmg))
        
        logic.current_weather = "sandstorm"
        logic.weather_turns = 5
        logger_obj.log("沙暴刮起来了！\n\n")
