import asyncio
import os

from twilio.rest import Client


def get_client() -> Client:
    return Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])


async def send_messages(from_number: str, to_number: str, texts: list[str]) -> None:
    client = get_client()
    for text in texts:
        await asyncio.to_thread(
            client.messages.create, from_=from_number, to=to_number, body=text
        )