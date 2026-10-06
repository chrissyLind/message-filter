import asyncio
import json
import os
from datetime import UTC, datetime

import boto3


def get_client():
    return boto3.client("s3")


def archive_key(message_sid: str, received_at: datetime) -> str:
    return f"messages/{received_at:%Y/%m/%d}/{message_sid}.json"


async def archive_message(
    message_sid: str, sender: str, body: str, received_at: datetime | None = None
) -> str:
    if received_at is None:
        received_at = datetime.now(UTC)
    key = archive_key(message_sid, received_at)
    record = {
        "message_sid": message_sid,
        "forwarded_by": sender,
        "received_at": received_at.isoformat(),
        "body": body,
    }
    await asyncio.to_thread(
        get_client().put_object,
        Bucket=os.environ["ARCHIVE_BUCKET"],
        Key=key,
        Body=json.dumps(record, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json",
    )
    return key