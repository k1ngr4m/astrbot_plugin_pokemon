"""
给 user_pokemon 表添加 ability_id 字段，并为现有宝可梦随机分配非隐藏特性
"""
from typing import Any
import sqlite3
import random
from astrbot.api import logger


def up(cursor) -> None:
    """
    添加 ability_id 字段到 user_pokemon 表
    """
    # 1. 添加 ability_id 字段
    try:
        cursor.execute("ALTER TABLE user_pokemon ADD COLUMN ability_id INTEGER DEFAULT NULL")
        logger.info("成功添加 ability_id 字段到 user_pokemon 表")
    except sqlite3.OperationalError as e:
        # 如果字段已存在，忽略错误
        if "duplicate column name" in str(e):
            logger.info("ability_id 字段已存在于 user_pokemon 表中")
        else:
            raise e

    # 2. 为现有的用户宝可梦随机分配特性
    try:
        # 获取所有未删除的用户宝可梦记录
        cursor.execute("""
            SELECT id, species_id FROM user_pokemon
            WHERE isdel = 0 AND ability_id IS NULL
        """)
        user_pokemon_records = cursor.fetchall()

        if user_pokemon_records:
            logger.info(f"为 {len(user_pokemon_records)} 个现有用户宝可梦分配特性...")

            for user_pokemon_id, species_id in user_pokemon_records:
                # 获取该宝可梦种族的非隐藏特性
                cursor.execute("""
                    SELECT ability_id FROM pokemon_abilities
                    WHERE pokemon_id = ? AND is_hidden = 0 AND slot IN (1, 2)
                    ORDER BY slot
                """, (species_id,))
                abilities = cursor.fetchall()

                if abilities:
                    # 随机选择一个非隐藏特性
                    selected_ability_id = random.choice(abilities)[0]

                    # 更新用户宝可梦的特性
                    cursor.execute("""
                        UPDATE user_pokemon
                        SET ability_id = ?
                        WHERE id = ?
                    """, (selected_ability_id, user_pokemon_id))
                else:
                    # 如果找不到非隐藏特性，则随机选择一个任何特性
                    cursor.execute("""
                        SELECT ability_id FROM pokemon_abilities
                        WHERE pokemon_id = ?
                        ORDER BY slot
                    """, (species_id,))
                    all_abilities = cursor.fetchall()

                    if all_abilities:
                        selected_ability_id = random.choice(all_abilities)[0]
                        cursor.execute("""
                            UPDATE user_pokemon
                            SET ability_id = ?
                            WHERE id = ?
                        """, (selected_ability_id, user_pokemon_id))

            logger.info(f"成功为 {len(user_pokemon_records)} 个用户宝可梦分配了特性")
        else:
            logger.info("没有需要分配特性的用户宝可梦")

        # 3. 添加外键约束
        # 由于SQLite的限制，我们需要创建新表并迁移数据，但我们先添加一个外键约束说明
        # 为 ability_id 字段添加索引以提高查询性能
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_pokemon_ability_id ON user_pokemon(ability_id)")

        logger.info("用户宝可梦特性分配完成")
    except Exception as e:
        logger.error(f"分配用户宝可梦特性时发生错误: {e}")
        raise e


def down(cursor) -> None:
    """
    回滚迁移 - 移除 ability_id 字段
    注意：SQLite 不支持直接删除字段，所以这个操作可能无法完全回滚
    """
    # 由于SQLite限制，我们不能直接删除列，所以这里只是删除索引
    cursor.execute("DROP INDEX IF EXISTS idx_user_pokemon_ability_id")
    # 警告用户无法完全回滚
    logger.warning("SQLite无法删除列，user_pokemon表的ability_id字段将保留")