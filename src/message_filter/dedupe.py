import os
from functools import cache
from typing import Literal

import redis.asyncio as redis

PROCESSING_SECONDS = 45
DONE_SECONDS = 7 * 24 * 60 * 60


@cache
def get_client() -> redis.Redis:
    return redis.from_url(os.environ["REDIS_URL"], decode_responses=True)


def job_key(message_sid: str) -> str:
    return f"job:{message_sid}"


async def claim(message_sid: str) -> Literal["new", "processing", "done"]:
    key = job_key(message_sid)
    claimed = await get_client().set(key, "processing", nx=True, ex=PROCESSING_SECONDS)
    if claimed:
        return "new"
    state = await get_client().get(key)
    return "done" if state == "done" else "processing"


async def mark_done(message_sid: str) -> None:
    await get_client().set(job_key(message_sid), "done", ex=DONE_SECONDS)


async def release(message_sid: str) -> None:
    await get_client().delete(job_key(message_sid))