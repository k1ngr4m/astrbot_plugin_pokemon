from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from ...core.models.user_models import User, UserTeam, UserItems
from ...core.models.pokemon_models import PokemonSpecies, UserPokemonInfo, \
    WildPokemonInfo, WildPokemonEncounterLog, PokemonMoves
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

class AbstractBattleRepository(ABC):
    """战斗日志数据仓储接口"""
    # ==========增==========
    # 添加战斗日志
    @abstractmethod
    def save_battle_log(self, user_id: str, target_name: str, log_data: List[str], result: str) -> None: pass

    @abstractmethod
    def get_battle_log_by_id(self, battle_log_id: int) -> Optional[Dict[str, Any]]: pass

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
    # 更新用户宝可梦经验
    @abstractmethod
    def update_user_pokemon_exp(self, level: int, exp: int, pokemon_id: int, user_id: str) -> None: pass

    # 更新宝可梦属性
    @abstractmethod
    def update_pokemon_attributes(self, attributes: Dict[str, int], pokemon_id: int, user_id: str) -> None: pass

    # 更新野生宝可梦遇到记录（如捕捉或战斗结果）
    @abstractmethod
    def update_encounter_log(self, log_id: int, is_captured: int = None,
                            is_battled: int = None, battle_result: str = None, isdel: int = None) -> None: pass

    # 更新用户宝可梦技能
    @abstractmethod
    def update_pokemon_moves(self, moves: PokemonMoves, pokemon_id: int, user_id: str) -> None: pass


    # ==========查==========
    # 获取用户所有宝可梦
    @abstractmethod
    def get_user_pokemon(self, user_id: str) -> List[UserPokemonInfo]: pass

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