import asyncio

import anthropic
import pytest

import message_filter.reply as reply_module
from message_filter.models import FilteredMessage
import message_filter.llm as llm_module


@pytest.mark.llm
def test_offers_two_or_three_options(monkeypatch):
    monkeypatch.setattr(llm_module, "client", anthropic.AsyncAnthropic())
    summary = FilteredMessage(
        facts=[
            "Your ex asks whether you can have Sam on October 17, 2026 "
            "instead of October 10, 2026"
        ],
        needs_reply=True,
        questions=["Can you have Sam on October 17, 2026 instead of October 10, 2026?"],
        notes=[],
    )

    drafts = asyncio.run(reply_module.draft_replies(summary))

    assert 2 <= len(drafts.options) <= 3
    for option in drafts.options:
        assert option.label
        assert option.text