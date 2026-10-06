import asyncio
import os

import boto3
from pydantic import BaseModel


class Job(BaseModel):
    message_sid: str
    body: str
    recipient: str
    sandbox_number: str


def get_client():
    return boto3.client("sqs")


async def enqueue(job: Job) -> None:
    await asyncio.to_thread(
        get_client().send_message,
        QueueUrl=os.environ["QUEUE_URL"],
        MessageBody=job.model_dump_json(),
    )


async def receive() -> tuple[Job, str] | None:
    response = await asyncio.to_thread(
        get_client().receive_message,
        QueueUrl=os.environ["QUEUE_URL"],
        MaxNumberOfMessages=1,
        WaitTimeSeconds=20,
    )
    messages = response.get("Messages", [])
    if not messages:
        return None
    message = messages[0]
    return Job.model_validate_json(message["Body"]), message["ReceiptHandle"]


async def delete(receipt_handle: str) -> None:
    await asyncio.to_thread(
        get_client().delete_message,
        QueueUrl=os.environ["QUEUE_URL"],
        ReceiptHandle=receipt_handle,
    )