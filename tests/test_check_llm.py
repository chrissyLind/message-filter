import asyncio
from datetime import date

import anthropic
import pytest

import message_filter.check as check_module
from message_filter.models import FilteredMessage
import message_filter.llm as llm_module
from message_filter.llm import SENDER

TEST_DATE = date(2026, 10, 3)
MESSAGE = (
    "Why is everything always so hard with you? I need to switch weekends. "
    "Can you take Sam on the 17th instead of the 10th?"
)


def run_check(summary, monkeypatch):
    monkeypatch.setattr(llm_module, "client", anthropic.AsyncAnthropic())
    return asyncio.run(check_module.check_summary(MESSAGE, summary, today=TEST_DATE))


@pytest.mark.llm
def test_catches_reversed_roles(monkeypatch):
    summary = FilteredMessage(
        facts=[f"{SENDER} wants to have Sam on October 17, 2026 instead of October 10, 2026"],
        needs_reply=False,
        questions=[],
        notes=[],
    )

    result = run_check(summary, monkeypatch)

    assert "incorrect" in [problem.kind for problem in result.problems]


@pytest.mark.llm
def test_accepts_a_correct_summary(monkeypatch):
    summary = FilteredMessage(
        facts=[
            f"{SENDER} asks whether you can have Sam on October 17, 2026 "
            "instead of October 10, 2026"
        ],
        needs_reply=True,
        questions=["Can you have Sam on October 17, 2026 instead of October 10, 2026?"],
        notes=[],
    )

    result = run_check(summary, monkeypatch)

    assert result.problems == []