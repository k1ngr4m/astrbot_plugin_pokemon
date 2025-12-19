"""
修复用户宝可梦的特性分配问题，确保所有宝可梦都有特性
"""
from typing import Any
import sqlite3
import random
from astrbot.api import logger


def up(cursor) -> None:
    """
    修复用户宝可梦，确保所有记录都有特性
    """
    try:
        # 获取所有未删除且没有特性的用户宝可梦记录
        cursor.execute("""
            SELECT id, species_id FROM user_pokemon
            WHERE isdel = 0 AND (ability_id IS NULL OR ability_id = 0)
        """)
        user_pokemon_records = cursor.fetchall()

        if user_pokemon_records:
            logger.info(f"为 {len(user_pokemon_records)} 个没有特性的用户宝可梦分配特性...")

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

        logger.info("用户宝可梦特性修复完成")
    except Exception as e:
        logger.error(f"修复用户宝可梦特性时发生错误: {e}")
        raise e


def down(cursor) -> None:
    """
    回滚修复
    """
    # 将所有能力ID设置为NULL
    cursor.execute("UPDATE user_pokemon SET ability_id = NULL WHERE isdel = 0")
    logger.info("已回滚用户宝可梦特性修复")