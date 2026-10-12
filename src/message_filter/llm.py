from datetime import date
from collections.abc import Callable
import logging

import anthropic
from pydantic import BaseModel

from message_filter.clock import local_today


logger = logging.getLogger(__name__)

SENDER = "your ex"
HAIKU = "claude-haiku-4-5-20251001"
SONNET = "claude-sonnet-5-5"

client = anthropic.AsyncAnthropic()


def format_today(today: date | None = None) -> str:
    if today is None:
        today = local_today()
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


MAX_TOOL_ROUNDS = 5


async def ask_with_tools[T: BaseModel](
    model: str,
    system: str,
    content: str,
    output_format: type[T],
    tools: list[dict],
    run_tool: Callable[[str, dict], str],
) -> T:
    messages = [{"role": "user", "content": content}]

    for _ in range(MAX_TOOL_ROUNDS):
        response = await client.messages.parse(
            model=model,
            max_tokens=4096,
            system=system,
            messages=messages,
            tools=tools,
            output_format=output_format,
        )

        if response.stop_reason != "tool_use":
            if response.parsed_output is None:
                raise RuntimeError("The model returned no result")
            return response.parsed_output

        messages.append({"role": "assistant", "content": response.content})

        results = []
        for block in response.content:
            if block.type == "tool_use":
                logger.info("Tool requested: %s", block.name)
                try:
                    output = run_tool(block.name, block.input)
                    results.append(
                        {"type": "tool_result", "tool_use_id": block.id, "content": output}
                    )
                except Exception as error:
                    results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(error),
                            "is_error": True,
                        }
                    )
        messages.append({"role": "user", "content": results})

    raise RuntimeError("The model kept asking for tools and never finished")