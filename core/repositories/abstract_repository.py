from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from ..domain.user_models import User, UserTeam, UserItems
from ..domain.pokemon_models import PokemonCreateResult, PokemonTemplate, UserPokemonInfo, PokemonDetail, \
    WildPokemonInfo, WildPokemonEncounterLog
from ..domain.adventure_models import AdventureArea, AreaPokemon, AreaInfo
from ..domain.shop_models import Shop, ShopItem

class AbstractUserRepository(ABC):
    """用户数据仓储接口"""

    # ==========增==========
    # 新增一个用户
    @abstractmethod
    def create_user(self, user: User) -> None: pass

    # 创建用户宝可梦记录
    @abstractmethod
    def create_user_pokemon(self, user_id: str, pokemon: UserPokemonInfo) -> int: pass

    # 为用户添加签到记录
    @abstractmethod
    def add_user_checkin(self, user_id: str, checkin_date: str, gold_reward: int, item_reward_id: int = 1, item_quantity: int = 1) -> None: pass

    # 为用户添加物品
    @abstractmethod
    def add_user_item(self, user_id: str, item_id: int, quantity: int) -> None: pass


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
    def get_by_id(self, user_id: str) -> Optional[User]: pass

    # 检查用户是否存在
    @abstractmethod
    def check_exists(self, user_id: str) -> bool: pass

    # 获取用户的所有宝可梦
    @abstractmethod
    def get_user_pokemon(self, user_id: str) -> List[UserPokemonInfo]: pass

    # 根据宝可梦ID获取用户宝可梦记录
    @abstractmethod
    def get_user_pokemon_by_id(self, user_id: str, pokemon_id: int) -> Optional[UserPokemonInfo]: pass

    # 检查用户今日是否已签到
    @abstractmethod
    def has_user_checked_in_today(self, user_id: str, today: str) -> bool: pass

    # 获取用户的所有物品
    @abstractmethod
    def get_user_items(self, user_id: str) -> UserItems: pass


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

    # 添加物品模板
    @abstractmethod
    def add_item_template(self, item_data: Dict[str, Any]) -> None: pass

    # 添加宝可梦招式模板
    @abstractmethod
    def add_pokemon_move_template(self, move_data: Dict[str, Any]) -> None: pass

    # 添加宝可梦物种招式模板
    @abstractmethod
    def add_pokemon_species_move_template(self, species_move_data: Dict[str, Any]) -> None: pass

    # 添加野生宝可梦遇到记录
    @abstractmethod
    def add_user_encountered_wild_pokemon(self, user_id: str, wild_pokemon: WildPokemonInfo, area_info: AreaInfo, encounter_rate: float) -> None: pass

    # ==========改==========
    # 更新宝可梦经验
    @abstractmethod
    def update_pokemon_exp(self, level: int, exp: int, pokemon_id: int, user_id: str) -> None: pass

    # 更新宝可梦属性
    @abstractmethod
    def update_pokemon_attributes(self, attributes: Dict[str, int], pokemon_id: int, user_id: str) -> None: pass

    # 更新野生宝可梦遇到记录（如捕捉或战斗结果）
    @abstractmethod
    def update_encounter_log(self, log_id: int, is_captured: int = None,
                            is_battled: int = None, battle_result: str = None) -> None: pass

    # ==========查==========
    # 获取宝可梦模板
    @abstractmethod
    def get_pokemon_by_id(self, pokemon_id: int) -> Optional[PokemonTemplate]: pass

    # 获取所有Pokemon模板
    @abstractmethod
    def get_all_pokemon(self) -> List[PokemonTemplate]: pass

    # 获取宝可梦类型
    @abstractmethod
    def get_pokemon_types(self, species_id: int) -> List[str]: pass

    # 获取用户正在遭遇的野生宝可梦
    @abstractmethod
    def get_user_encountered_wild_pokemon(self, user_id: str) -> Optional[WildPokemonEncounterLog]: pass

    # 获取用户遇到的所有野生宝可梦记录
    @abstractmethod
    def get_user_encounters(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]: pass

    # 获取用户遇到的某个特定物种的次数
    @abstractmethod
    def get_user_pokemon_encounter_count(self, user_id: str, pokemon_species_id: int) -> int: pass

    # 统计用户的总遇到次数
    @abstractmethod
    def get_user_total_encounters(self, user_id: str) -> int: pass

    # 获取最新的遇到记录
    @abstractmethod
    def get_latest_encounters(self, limit: int = 10) -> List[Dict[str, Any]]: pass

class AbstractTeamRepository(ABC):
    """队伍数据仓储接口"""

    # ==========改==========
    # 更新用户的队伍配置
    @abstractmethod
    def update_user_team(self, user_id: str, team_data: UserTeam) -> None: pass


    # ==========查==========
    # 获取用户的队伍配置
    @abstractmethod
    def get_user_team(self, user_id: str) -> UserTeam: pass


class AbstractAdventureRepository(ABC):
    """冒险区域数据仓储接口"""

    # ==========增==========
    # 添加冒险区域模板
    @abstractmethod
    def add_area_template(self, area: Dict[str, Any]) -> None: pass

    # 添加区域内宝可梦模板
    @abstractmethod
    def add_area_pokemon_template(self, area_pokemon: Dict[str, Any]) -> None: pass


    # ==========查==========
    # 获取所有冒险区域
    @abstractmethod
    def get_all_areas(self) -> List[AdventureArea]: pass

    # 根据区域编码获取区域
    @abstractmethod
    def get_area_by_code(self, area_code: str) -> Optional[AdventureArea]: pass

    # 根据区域ID获取区域内的宝可梦
    @abstractmethod
    def get_area_pokemon_by_area_id(self, area_id: int) -> List[AreaPokemon]: pass

    # 根据区域编码获取区域内的宝可梦
    @abstractmethod
    def get_area_pokemon_by_area_code(self, area_code: str) -> List[AreaPokemon]: pass


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
    # 根据商店编码获取商店
    @abstractmethod
    def get_shop_by_code(self, shop_code: str) -> Optional[Shop]: pass
    # 根据商店ID获取商店内的物品
    @abstractmethod
    def get_shop_items_by_shop_id(self, shop_id: int) -> List[Dict[str, Any]]: pass
    # 检查商店是否存在
    @abstractmethod
    def check_shop_exists_by_code(self, shop_code: str) -> bool: pass
    # 根据商店物品ID获取商店物品
    @abstractmethod
    def get_a_shop_item_by_id(self, shop_item_id: int, shop_id: int) -> Optional[Dict[str, Any]]: pass
