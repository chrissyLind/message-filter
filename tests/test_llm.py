import asyncio
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

import message_filter.llm as llm_module


class Answer(BaseModel):
    text: str


class FakeMessages:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    async def parse(self, **kwargs):
        self.requests.append({**kwargs, "messages": list(kwargs["messages"])})
        return self.responses.pop(0)


def tool_request(name, tool_input):
    block = SimpleNamespace(type="tool_use", name=name, input=tool_input, id="toolu_1")
    return SimpleNamespace(stop_reason="tool_use", content=[block], parsed_output=None)


def final_answer(result):
    return SimpleNamespace(stop_reason="end_turn", content=[], parsed_output=result)


def ask(fake, run_tool, monkeypatch):
    monkeypatch.setattr(llm_module, "client", SimpleNamespace(messages=fake))
    return asyncio.run(
        llm_module.ask_with_tools("model", "system", "question", Answer, [], run_tool)
    )


def test_runs_the_tool_and_sends_the_result_back(monkeypatch):
    fake = FakeMessages(
        [
            tool_request("next_weekday", {"weekday": "friday"}),
            final_answer(Answer(text="done")),
        ]
    )
    calls = []

    def run_tool(name, tool_input):
        calls.append((name, tool_input))
        return "Friday, October 09, 2026"

    result = ask(fake, run_tool, monkeypatch)

    assert result == Answer(text="done")
    assert calls == [("next_weekday", {"weekday": "friday"})]
    assert fake.requests[1]["messages"][2]["content"][0] == {
        "type": "tool_result",
        "tool_use_id": "toolu_1",
        "content": "Friday, October 09, 2026",
    }


def test_reports_a_tool_error_to_the_model(monkeypatch):
    fake = FakeMessages(
        [tool_request("no_such_tool", {}), final_answer(Answer(text="done"))]
    )

    def run_tool(name, tool_input):
        raise ValueError(f"Unknown tool: {name}")

    result = ask(fake, run_tool, monkeypatch)

    tool_result = fake.requests[1]["messages"][2]["content"][0]
    assert result == Answer(text="done")
    assert tool_result["is_error"] is True
    assert "Unknown tool" in tool_result["content"]


def test_gives_up_after_too_many_rounds(monkeypatch):
    fake = FakeMessages([tool_request("next_weekday", {"weekday": "friday"})] * 10)

    with pytest.raises(RuntimeError):
        ask(fake, lambda name, tool_input: "Friday", monkeypatch)

    assert len(fake.requests) == llm_module.MAX_TOOL_ROUNDS