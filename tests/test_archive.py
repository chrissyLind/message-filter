import asyncio
import json
from datetime import UTC, datetime
from types import SimpleNamespace

import message_filter.archive as archive_module

RECEIVED = datetime(2026, 10, 6, 15, 30, tzinfo=UTC)


def test_key_is_built_from_the_date_and_message_id():
    assert archive_module.archive_key("SM123", RECEIVED) == "messages/2026/10/06/SM123.json"


def test_stores_the_message_as_json(monkeypatch):
    calls = []
    fake_client = SimpleNamespace(put_object=lambda **kwargs: calls.append(kwargs))
    monkeypatch.setattr(archive_module, "get_client", lambda: fake_client)
    monkeypatch.setenv("ARCHIVE_BUCKET", "test-bucket")

    key = asyncio.run(
        archive_module.archive_message("SM123", "whatsapp:+1", "Pickup at 5:30", RECEIVED)
    )

    assert key == "messages/2026/10/06/SM123.json"
    assert calls[0]["Bucket"] == "test-bucket"
    assert calls[0]["Key"] == key
    assert json.loads(calls[0]["Body"]) == {
        "message_sid": "SM123",
        "forwarded_by": "whatsapp:+1",
        "received_at": "2026-10-06T15:30:00+00:00",
        "body": "Pickup at 5:30",
    }