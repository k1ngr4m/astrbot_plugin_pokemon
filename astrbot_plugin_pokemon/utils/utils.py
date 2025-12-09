import base64
import random
from datetime import datetime, date, timedelta, timezone
from typing import List, Tuple, Any
import re
import socket
import os
import platform
import signal
import subprocess
import time

import aiohttp
import asyncio

from astrbot.api import logger

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


# 获取当前的UTC+8时间
def get_now() -> datetime:
    return datetime.now(timezone(timedelta(hours=8)))


def get_today() -> date:
    return get_now().date()


def userid_to_base32(userid: str) -> str:
    return base64.b32encode(userid.encode("utf-8")).decode("utf-8")[:32]


async def _is_port_available(port: int) -> bool:
    """异步检查端口是否可用，避免阻塞事件循环"""

    def check_sync():
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("0.0.0.0", port))
            return True
        except OSError:
            return False

    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, check_sync)
    except Exception as e:
        logger.warning(f"检查端口 {port} 可用性时出错: {e}")
        return False
