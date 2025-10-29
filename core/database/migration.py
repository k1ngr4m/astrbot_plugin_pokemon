import sqlite3
import os
import re
import importlib

from astrbot.api import logger
def run_migrations(db_path: str, migrations_dir: str):
    """
    运行所有待处理的数据库迁移脚本。
    """
    pass