from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any

from ...core.models.trainer_models import TrainerEncounter, TrainerLocation, TrainerPokemon, Trainer
from ...core.models.user_models import User, UserTeam, UserItems
from ...core.models.pokemon_models import PokemonSpecies, UserPokemonInfo, \
    WildPokemonInfo, WildPokemonEncounterLog, PokemonMoves, PokemonEvolutionInfo
from ...core.models.adventure_models import LocationTemplate, LocationPokemon
from ...core.models.shop_models import Shop


class AbstractUserRepository(ABC):
    """用户数据仓储接口"""
    # ==========增==========
    # 新增一个用户
    @abstractmethod
    def add_pokemon_user(self, user: User) -> None: pass

    # 为用户添加签到记录
    @abstractmethod
    def add_user_checkin(self, user_id: str, checkin_date: str, gold_reward: int, item_reward_id: int, item_quantity: int) -> None: pass

    # ==========改==========
    # 更新用户的初始选择状态
    @abstractmethod
    def update_init_select(self, user_id: str, pokemon_id: int) -> None: pass

    @abstractmethod
    def update_user_exp(self, level: int, exp: int, user_id: str) -> None: pass

    # 更新用户的金币数量
    @abstractmethod
    def update_user_coins(self, user_id: str, coins: int) -> None: pass

    # ==========查==========
    # 根据ID获取用户
    @abstractmethod
    def get_user_by_id(self, user_id: str) -> Optional[User]: pass

    # 检查用户今日是否已签到
    @abstractmethod
    def has_user_checked_in_today(self, user_id: str, today: str) -> bool: pass

    @abstractmethod
    def update_user_last_adventure_time(self, user_id, last_adventure_time): pass

    @abstractmethod
    def get_all_users(self) -> List[User]: pass

class AbstractPokemonRepository(ABC):
    """宝可梦数据仓储接口"""
    # ==========增==========
    # 添加宝可梦模板
    @abstractmethod
    def add_pokemon_template(self, pokemon_data: Dict[str, Any]) -> None: pass

    # 添加宝可梦类型模板
    @abstractmethod
    def add_pokemon_type_template(self, type_data: Dict[str, Any]) -> None: pass

    # 添加宝可梦物种类型模板
    @abstractmethod
    def add_pokemon_species_type_template(self, species_type_data: Dict[str, Any]) -> None: pass

    # 添加宝可梦进化模板
    @abstractmethod
    def add_pokemon_evolution_template(self, evolution_data: Dict[str, Any]) -> None: pass

    # 添加野生宝可梦
    @abstractmethod
    def add_wild_pokemon(self, wild_pokemon_info: WildPokemonInfo) -> int: pass

    # 添加宝可梦模板批量
    @abstractmethod
    def add_pokemon_templates_batch(self, pokemon_data_list: List[Dict[str, Any]]) -> None: pass

    # 添加宝可梦进化模板批量
    @abstractmethod
    def add_pokemon_evolutions_batch(self, type_data_list: List[Dict[str, Any]]) -> None: pass

    # ==========改==========


    # ==========查==========
    # 获取宝可梦模板
    @abstractmethod
    def get_pokemon_by_id(self, pokemon_id: int) -> Optional[PokemonSpecies]: pass

    # 根据名称获取宝可梦物种信息
    @abstractmethod
    def get_pokemon_by_name(self, pokemon_name: str) -> Optional[PokemonSpecies]: pass

    # 获取所有Pokemon模板
    @abstractmethod
    def get_all_pokemon(self) -> List[PokemonSpecies]: pass

    # 获取宝可梦类型
    @abstractmethod
    def get_pokemon_types(self, species_id: int) -> List[str]: pass

    @abstractmethod
    def get_pokemon_species_types(self, species_id: int) -> List[str]: pass

    # 获取宝可梦基础经验值
    @abstractmethod
    def get_base_exp(self, pokemon_id: int) -> int: pass

    # 获取野生宝可梦模板
    @abstractmethod
    def get_wild_pokemon_by_id(self, wild_pokemon_id: int) -> Optional[WildPokemonInfo]: pass

    # 获取宝可梦捕获率
    @abstractmethod
    def get_pokemon_capture_rate(self, pokemon_id: int) -> int: pass

    # 获取所有宝可梦模板（简单信息）
    @abstractmethod
    def get_all_pokemon_simple(self) -> List[PokemonSpecies]: pass

    # 获取宝可梦进化数据
    @abstractmethod
    def get_pokemon_evolutions(self, species_id: int, new_level: int) -> list[PokemonEvolutionInfo]: pass


class AbstractAdventureRepository(ABC):
    """冒险区域数据仓储接口"""
    # ==========增==========
    # 添加冒险区域模板
    @abstractmethod
    def add_location_template(self, location: Dict[str, Any]) -> None: pass

    # 添加区域内宝可梦模板
    @abstractmethod
    def add_location_pokemon_template(self, location_pokemon: Dict[str, Any]) -> None: pass


    # ==========查==========
    # 获取所有冒险区域
    @abstractmethod
    def get_all_locations(self) -> List[LocationTemplate]: pass

    # 根据区域编码获取区域
    @abstractmethod
    def get_location_by_id(self, location_id: int) -> Optional[LocationTemplate]: pass

    # 根据区域ID获取区域内的宝可梦
    @abstractmethod
    def get_location_pokemon_by_location_id(self, location_id: int) -> List[LocationPokemon]: pass

class AbstractShopRepository(ABC):
    """商店数据仓储接口"""
    # ==========增==========
    # 添加商店模板
    @abstractmethod
    def add_shop_template(self, shop: Dict[str, Any]) -> None: pass

    # 添加商店物品模板
    @abstractmethod
    def add_shop_item_template(self, shop_item: Dict[str, Any]) -> None: pass


    # ==========改==========
    # 更新商店物品库存
    @abstractmethod
    def update_shop_item_stock(self, shop_item_id: int, stock: int) -> None: pass


    # ==========查==========
    # 获取所有活跃商店
    @abstractmethod
    def get_active_shops(self) -> List[Shop]: pass

    # 根据商店ID获取商店
    @abstractmethod
    def get_shop_by_id(self, shop_id: int) -> Optional[Shop]: pass

    # 根据商店ID获取商店内的物品
    @abstractmethod
    def get_shop_items_by_shop_id(self, shop_id: int) -> List[Dict[str, Any]]: pass

    # 根据商店物品ID获取商店物品
    @abstractmethod
    def get_a_shop_item_by_id(self, shop_item_id: int, shop_id: int) -> Optional[Dict[str, Any]]: pass

class AbstractItemRepository(ABC):
    """物品数据仓储接口"""
    # ==========增==========
    # 添加物品模板
    @abstractmethod
    def add_item_template(self, item_data: Dict[str, Any]) -> None: pass

    # ==========查==========
    # 根据物品ID获取物品名称
    @abstractmethod
    def get_item_name(self, item_id: int) -> Optional[str]: pass

class AbstractMoveRepository(ABC):
    """技能数据仓储接口"""
    # ==========增==========
    # 添加技能模板
    @abstractmethod
    def add_move_template(self, move_data: Dict[str, Any]) -> None: pass

    # 添加宝可梦物种招式模板
    @abstractmethod
    def add_pokemon_species_move_template(self, pokemon_moves_data: Dict[str, Any]) -> None: pass

    # 批量添加宝可梦物种招式模板
    @abstractmethod
    def add_pokemon_species_move_templates_batch(self, pokemon_moves_list: List[Dict[str, Any]]) -> None: pass

    # 获取宝可梦升级招式
    @abstractmethod
    def get_level_up_moves(self, pokemon_species_id: int, level: int) -> List[int]: pass

    # 获取宝可梦在指定等级范围内新学会的升级招式
    @abstractmethod
    def get_moves_learned_in_level_range(self, pokemon_species_id: int, min_level: int, max_level: int) -> List[int]: pass

    # 获取招式详细信息
    @abstractmethod
    def get_move_by_id(self, move_id: int) -> Dict[str, Any] | None: pass

    @abstractmethod
    def get_pokemon_moves_by_species_id(self, pokemon_species_id: int) -> List[Dict[str, Any]]: pass

    @abstractmethod
    def add_move_flag_map_templates_batch(self, data_list: List[Dict[str, Any]]) -> None: pass

    @abstractmethod
    def add_move_meta_templates_batch(self, data_list: List[Dict[str, Any]]) -> None: pass

    @abstractmethod
    def add_move_stat_change_templates_batch(self, data_list: List[Dict[str, Any]]) -> None: pass

    @abstractmethod
    def get_move_meta_by_move_id(self, move_id: int) -> Optional[Dict[str, Any]]: pass

    @abstractmethod
    def get_move_stat_changes_by_move_id(self, move_id: int) -> List[Dict[str, Any]]: pass

    @abstractmethod
    def get_moves_by_ids(self, move_ids: List[int]) -> Dict[int, Dict[str, Any]]: pass

    @abstractmethod
    def get_move_by_name(self, move_name: str) -> Dict[str, Any] | None: pass

class AbstractBattleRepository(ABC):
    """战斗日志数据仓储接口"""
    # ==========增==========
    # 添加战斗日志
    @abstractmethod
    def save_battle_log(self, user_id: str, target_name: str, log_data: List[str], result: str) -> None: pass

    @abstractmethod
    def get_battle_log_by_id(self, battle_log_id: int) -> Optional[Dict[str, Any]]: pass

    @abstractmethod
    def get_user_battle_logs(self, user_id: str, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]: pass

class AbstractTeamRepository(ABC):
    """队伍数据仓储接口"""
    # ==========改==========
    # 更新用户的队伍配置
    @abstractmethod
    def update_user_team(self, user_id: str, team_data: UserTeam) -> None: pass


    # ==========查==========
    # 获取用户的队伍配置
    @abstractmethod
    def get_user_team(self, user_id: str) -> UserTeam | None: pass


# ==========联合repo==========
class AbstractUserPokemonRepository(ABC):
    """用户宝可梦数据仓储接口"""
    # ==========增==========
    # 创建用户宝可梦记录
    @abstractmethod
    def create_user_pokemon(self, user_id: str, pokemon: UserPokemonInfo) -> int: pass

    # 添加野生宝可梦遇到记录
    @abstractmethod
    def add_user_encountered_wild_pokemon(self, user_id: str, wild_pokemon_id: int, location_id: int, encounter_rate: float) -> None: pass


    # ==========改==========
    # 更新野生宝可梦遇到记录（如捕捉或战斗结果）
    @abstractmethod
    def update_encounter_log(self, log_id: int, is_captured: int = None,
                            is_battled: int = None, battle_result: str = None, isdel: int = None) -> None: pass

    @abstractmethod
    # 更新用户宝可梦字段
    def _update_user_pokemon_fields(self, user_id: str, pokemon_id: int, **kwargs) -> None: pass

    @abstractmethod
    def update_user_pokemon_happiness(self, user_id: str, pokemon_id: int, happiness: int) -> None: pass

    @abstractmethod
    def update_user_pokemon_current_hp(self, user_id: str, pokemon_id: int, current_hp: int) -> None: pass

    @abstractmethod
    def update_user_pokemon_current_pp(self, user_id: str, pokemon_id: int, current_pp1: int = None,
                                       current_pp2: int = None, current_pp3: int = None, current_pp4: int = None) -> None: pass

    @abstractmethod
    def update_user_pokemon_full_heal(self, user_id: str, pokemon_id: int) -> None: pass

    # ==========查==========
    # 获取用户所有宝可梦
    @abstractmethod
    def get_user_pokemon(self, user_id: str) -> List[UserPokemonInfo]: pass

    # 分页获取用户宝可梦
    @abstractmethod
    def get_user_pokemon_paged(self, user_id: str, limit: int, offset: int) -> List[UserPokemonInfo]: pass

    # 获取用户宝可梦总数
    @abstractmethod
    def get_user_pokemon_count(self, user_id: str) -> int: pass

    # 根据宝可梦ID获取用户宝可梦记录
    @abstractmethod
    def get_user_pokemon_by_id(self, user_id: str, pokemon_id: int) -> Optional[UserPokemonInfo]: pass

    # 获取用户图鉴的宝可梦ids
    @abstractmethod
    def get_user_pokedex_ids(self, user_id: str) -> dict[str, Any]: pass

    # 获取用户正在遭遇的野生宝可梦
    @abstractmethod
    def get_user_encountered_wild_pokemon(self, user_id: str) -> Optional[WildPokemonEncounterLog]: pass

    # 获取用户遇到的所有野生宝可梦记录
    @abstractmethod
    def get_user_encounters(self, user_id: str, limit: int = 50, offset: int = 0) -> List[WildPokemonEncounterLog]: pass

    # 获取最新的遇到记录
    @abstractmethod
    def get_latest_encounters(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]: pass

    # ==========训练家遭遇管理==========
    # 设置用户当前遭遇的训练家ID
    @abstractmethod
    def set_user_current_trainer_encounter(self, user_id: str, trainer_id: int) -> None: pass

    # 获取用户当前遭遇的训练家ID
    @abstractmethod
    def get_user_current_trainer_encounter(self, user_id: str) -> Optional[int]: pass

    # 清除用户当前遭遇的训练家ID
    @abstractmethod
    def clear_user_current_trainer_encounter(self, user_id: str) -> None: pass

    # ==========图鉴历史管理==========
    # 记录用户捕获的宝可梦物种到图鉴历史
    @abstractmethod
    def record_pokedex_capture(self, user_id: str, species_id: int) -> None: pass

class AbstractUserItemRepository(ABC):
    """用户物品数据仓储接口"""
    # ==========增==========
    # 添加用户物品
    @abstractmethod
    def add_user_item(self, user_id: str, item_id: int, amount: int) -> None: pass

    # ==========查==========
    # 获取用户的所有物品
    @abstractmethod
    def get_user_items(self, user_id: str) -> UserItems: pass


class AbstractNatureRepository(ABC):
    """性格数据仓储接口"""
    # ==========增==========
    # 添加性格模板
    @abstractmethod
    def add_nature_template(self, nature_data: Dict[str, Any]) -> None: pass

    # 批量添加性格模板
    @abstractmethod
    def add_nature_templates_batch(self, nature_data_list: List[Dict[str, Any]]) -> None: pass

    # 添加性格属性模板
    @abstractmethod
    def add_nature_stat_template(self, nature_stat_data: Dict[str, Any]) -> None: pass

    # 批量添加性格属性模板
    @abstractmethod
    def add_nature_stat_templates_batch(self, nature_stat_data_list: List[Dict[str, Any]]) -> None: pass

    # ==========查==========
    # 根据ID获取性格
    @abstractmethod
    def get_nature_by_id(self, nature_id: int) -> Optional[Dict[str, Any]]: pass

    # 获取所有性格
    @abstractmethod
    def get_all_natures(self) -> List[Dict[str, Any]]: pass

    # 根据性格ID获取性格属性
    @abstractmethod
    def get_nature_stats_by_nature_id(self, nature_id: int) -> List[Dict[str, Any]]: pass

class AbstractTrainerRepository(ABC):
    """训练家数据仓储接口"""
    # ==========增==========
    # 添加训练家
    @abstractmethod
    def create_trainer(self, trainer: Trainer) -> None: pass

    @abstractmethod
    def create_trainers_batch(self, trainers_list: List[Trainer]) -> None: pass

    # 添加训练家宝可梦
    @abstractmethod
    def create_trainer_pokemon(self, trainer_pokemon: TrainerPokemon) -> None: pass

    @abstractmethod
    def create_trainer_pokemons_batch(self, trainer_pokemons_list: List[TrainerPokemon]) -> None: pass

    # 添加训练家位置记录
    @abstractmethod
    def create_location_trainers(self, location_trainer: TrainerLocation) -> None: pass

    @abstractmethod
    def create_location_trainers_batch(self, location_trainers_list: List[TrainerLocation]) -> None: pass
    # ==========改==========
    # 更新训练家字段
    @abstractmethod
    def update_trainer_encounter(self, trainer_encounter_id: int, **kwargs) -> None: pass

    # ==========查==========
    # 根据ID获取训练家
    @abstractmethod
    def get_trainer_by_id(self, trainer_id: int) -> Optional[Dict[str, Any]]: pass

    # 获取所有训练家
    @abstractmethod
    def get_all_trainers(self) -> List[Dict[str, Any]]: pass

    # 根据训练家ID获取训练家宝可梦
    @abstractmethod
    def get_trainer_pokemon_by_trainer_id(self, trainer_id: int) -> List[Dict[str, Any]]: pass

    # 根据训练家遭遇ID获取训练家遭遇记录
    @abstractmethod
    def get_trainer_encounter_by_id(self, user_id: str, trainer_id: int) -> Optional[TrainerEncounter]: pass


    # 根据位置ID获取所有训练家
    @abstractmethod
    def get_trainers_at_location(self, location_id: int) -> List[Dict[str, Any]]: pass

    @abstractmethod
    def get_trainer_detail(self, trainer_id: int) -> Optional[Dict[str, Any]]: pass

    @abstractmethod
    def has_user_fought_trainer(self, user_id: str, trainer_id: int) -> bool: pass


class AbstractAbilityRepository(ABC):
    """宝可梦特性定义数据仓储接口"""
    # ==========增==========
    # 添加特性模板
    @abstractmethod
    def add_pokemon_ability_template(self, ability_data: Dict[str, Any]) -> None: pass

    # 批量添加特性模板
    @abstractmethod
    def add_pokemon_ability_templates_batch(self, ability_data_list: List[Dict[str, Any]]) -> None: pass

    # ==========查==========
    # 根据ID获取特性
    @abstractmethod
    def get_ability_by_id(self, ability_id: int) -> Optional[Dict[str, Any]]: pass

    # 获取所有特性
    @abstractmethod
    def get_all_abilities(self) -> List[Dict[str, Any]]: pass

    # 根据名称获取特性
    @abstractmethod
    def get_ability_by_name(self, name: str) -> Optional[Dict[str, Any]]: pass


class AbstractPokemonAbilityRepository(ABC):
    """宝可梦特性数据仓储接口（处理宝可梦与特性的关系）"""
    # ==========增==========
    # 添加宝可梦特性关联模板
    @abstractmethod
    def add_pokemon_ability_relation_template(self, relation_data: Dict[str, Any]) -> None: pass

    # 批量添加宝可梦特性关联模板
    @abstractmethod
    def add_pokemon_ability_relation_templates_batch(self, relation_data_list: List[Dict[str, Any]]) -> None: pass

    # ==========查==========
    # 根据宝可梦ID获取特性关联
    @abstractmethod
    def get_abilities_by_pokemon_id(self, pokemon_id: int) -> List[Dict[str, Any]]: pass

    # 根据宝可梦ID和特性ID获取关联
    @abstractmethod
    def get_ability_relation_by_pokemon_and_ability_id(self, pokemon_id: int, ability_id: int) -> Optional[Dict[str, Any]]: pass

    # 获取所有宝可梦特性关联
    @abstractmethod
    def get_all_pokemon_ability_relations(self) -> List[Dict[str, Any]]: pass
