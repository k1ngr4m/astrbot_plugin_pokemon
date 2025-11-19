import base64
import random
from datetime import datetime, date, timedelta, timezone
from typing import List, Tuple, Any

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


# 获取当前的UTC+8时间
def get_now() -> datetime:
    return datetime.now(timezone(timedelta(hours=8)))


def get_today() -> date:
    return get_now().date()


def userid_to_base32(userid: str) -> str:
    return base64.b32encode(userid.encode("utf-8")).decode("utf-8")[:32]