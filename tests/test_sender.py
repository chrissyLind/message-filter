import asyncio
from types import SimpleNamespace

import message_filter.sender as sender_module


def test_sends_each_text_in_order(monkeypatch):
    calls = []
    fake_client = SimpleNamespace(
        messages=SimpleNamespace(create=lambda **kwargs: calls.append(kwargs))
    )
    monkeypatch.setattr(sender_module, "get_client", lambda: fake_client)

    asyncio.run(sender_module.send_messages("whatsapp:+1", "whatsapp:+2", ["first", "second"]))

    assert [call["body"] for call in calls] == ["first", "second"]
    assert calls[0]["from_"] == "whatsapp:+1"
    assert calls[0]["to"] == "whatsapp:+2"