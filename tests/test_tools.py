from datetime import date

import pytest

from message_filter.tools import next_weekday, run_tool

SATURDAY = date(2026, 10, 3)


def test_finds_the_coming_friday():
    assert next_weekday("friday", SATURDAY) == date(2026, 10, 9)


def test_tomorrow_counts():
    assert next_weekday("sunday", SATURDAY) == date(2026, 10, 4)


def test_same_weekday_means_a_week_later():
    assert next_weekday("saturday", SATURDAY) == date(2026, 10, 10)


def test_ignores_capital_letters():
    assert next_weekday("Friday", SATURDAY) == date(2026, 10, 9)


def test_run_tool_returns_the_date_as_text():
    result = run_tool("next_weekday", {"weekday": "friday"}, SATURDAY)

    assert result == "Friday, October 09, 2026"


def test_run_tool_rejects_unknown_tools():
    with pytest.raises(ValueError):
        run_tool("delete_everything", {}, SATURDAY)