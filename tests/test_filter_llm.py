from datetime import date
import asyncio

import anthropic
import pytest

import message_filter.filter as filter_module
from message_filter.formatting import format_for_whatsapp

TEST_DATE = date(2026, 10, 3)
CASES = [
    pytest.param(
        "Why do you always have to make everything so difficult? I'll pick up Sam "
        "at 5:30 Friday from school, not 5. And send his inhaler this time, unlike "
        "last time when you completely forgot. Typical.",
        ["5:30", "inhaler"],
        ["typical", "difficult"],
        id="pickup-change-with-insults",
    ),
    pytest.param(
        "You are the most selfish person I have ever met. Everyone sees it.",
        [],
        ["selfish"],
        id="only-insults",
    ),
    pytest.param(
        "My lawyer is filing for full custody next week, so enjoy it while it lasts.",
        ["custody"],
        ["enjoy it while it lasts"],
        id="legal-mention",
    ),
    pytest.param(
        "I'll get the kids tomorrow afternoon around dinner time",
        ["NOTES", "your ex", "october", "4, 2026", "dinner"],
        [],
        id="vague time",
    ),
    pytest.param(
        "I do not understand why I continue to help you. Do you realize how much I do for you? Why do I even bother?",
        [],
        ["Do you realize"],
        id="rhetorical questions insults"
    ),
    pytest.param(
        "I'm leaving on October 5th, can't remember the time of day. So I won't be able to take G to practice that evening. "
        "Practice starts at 5pm at Southern Community Park. They'll be at their usual field. Can you please make sure he's "
        "there on time that week. Also you are on point that day to bring a snack for the team. They expect it at 6pm at the " 
        "end of practice. Hope that's not too much for you.",
        ["October 5", "southern community park", "snack", "6", "pm"],
        ["Hope that's not too much"],
        id="many details"
    ),
    pytest.param(
        "Why is everything always so hard with you? I need to switch weekends. Can you take Sam on the 17th instead of the 10th?",
        [],
        ["ex wants to take Sam on October 17"],
        id = "FACT mixup"
    )
]


@pytest.mark.llm
@pytest.mark.parametrize("message, must_include, must_exclude", CASES)
def test_filter(message, must_include, must_exclude, monkeypatch):
    monkeypatch.setattr(filter_module, "client", anthropic.AsyncAnthropic())

    filtered = asyncio.run(filter_module.filter_message(message, today=TEST_DATE))
    result = format_for_whatsapp(filtered).lower()

    for phrase in must_include:
        assert phrase.lower() in result, f"Missing '{phrase}' in:\n{result}"
    for phrase in must_exclude:
        assert phrase.lower() not in result, f"Should not contain '{phrase}':\n{result}"