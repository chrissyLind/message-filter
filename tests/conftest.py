import fakeredis
import pytest

from dotenv import load_dotenv
from message_filter import dedupe


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    server = fakeredis.FakeServer()
    monkeypatch.setattr(
        dedupe,
        "get_client",
        lambda: fakeredis.FakeAsyncRedis(server=server, decode_responses=True),
    )
    return server


load_dotenv()