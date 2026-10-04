import asyncio

import anthropic
import pytest

import message_filter.llm as llm_module
from message_filter.evaluate import judge

EXPECTED = (
    "Your ex asks whether you can have Sam on October 17, 2026 "
    "instead of October 10, 2026"
)


def run_judge(lines, monkeypatch):
    monkeypatch.setattr(llm_module, "client", anthropic.AsyncAnthropic())
    return asyncio.run(judge(EXPECTED, lines))


@pytest.mark.llm
def test_rejects_reversed_roles(monkeypatch):
    lines = ["Your ex wants to have Sam on October 17, 2026 instead of October 10, 2026"]

    assert run_judge(lines, monkeypatch).conveyed is False


@pytest.mark.llm
def test_accepts_the_same_meaning_in_other_words(monkeypatch):
    lines = ["Your ex is asking if you could take Sam on 10/17/2026 rather than 10/10/2026"]

    assert run_judge(lines, monkeypatch).conveyed is True


@pytest.mark.llm
def test_rejects_when_there_are_no_lines(monkeypatch):
    assert run_judge([], monkeypatch).conveyed is False