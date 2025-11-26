from typing import Dict, Any, Optional, List
from .abstract_repository import AbstractBattleRepository

from astrbot.api import logger
import sqlite3
import json

class SqliteBattleRepository(AbstractBattleRepository):
    def __init__(self, db_path: str):
        self.db_path = db_path

    def save_battle_log(self, user_id: str, target_name: str, log_data: List[str], result: str) -> int:
        """保存战斗日志，返回日志ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO battle_logs (user_id, target_name, log_data, result)
                    VALUES (?, ?, ?, ?)
                """, (user_id, target_name, json.dumps(log_data, ensure_ascii=False), result))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"保存战斗日志失败: {e}")
            return -1

    def get_battle_log_by_id(self, log_id: int) -> Optional[Dict[str, Any]]:
        """获取战斗日志"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, user_id, target_name, log_data, result, created_at
                    FROM battle_logs
                    WHERE id = ?
                """, (log_id,))
                row = cursor.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "user_id": row[1],
                        "target_name": row[2],
                        "log_data": json.loads(row[3]),
                        "result": row[4],
                        "created_at": row[5]
                    }
                return None
        except Exception as e:
            logger.error(f"获取战斗日志失败: {e}")
            return None
