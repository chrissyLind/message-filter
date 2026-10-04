from datetime import date

import anthropic
from pydantic import BaseModel

SENDER = "your ex"
HAIKU = "claude-haiku-4-5-20251001"
SONNET = "claude-sonnet-5-5"

client = anthropic.AsyncAnthropic()


def format_today(today: date | None = None) -> str:
    if today is None:
        today = date.today()
    return today.strftime("%A, %B %d, %Y")


async def ask[T: BaseModel](
    model: str, system: str, content: str, output_format: type[T]
) -> T:
    response = await client.messages.parse(
        model=model,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": content}],
        output_format=output_format,
    )
    if response.parsed_output is None:
        raise RuntimeError("The model returned no result")
    return response.parsed_output