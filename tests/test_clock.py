from datetime import date, datetime, timezone

from message_filter.clock import local_today


def test_late_evening_in_new_york_is_still_today():
    utc_now = datetime(2026, 10, 13, 1, 30, tzinfo=timezone.utc)

    assert local_today(utc_now) == date(2026, 10, 12)