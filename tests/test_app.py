import pytest
from fastapi.testclient import TestClient

import message_filter.app as app_module

MY_NUMBER = "whatsapp:+15550001111"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(app_module, "ALLOWED_SENDER", MY_NUMBER)
    return TestClient(app_module.app)


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_rejects_unknown_sender(client, monkeypatch):
    calls = []

    async def fake_filter(text):
        calls.append(text)
        return "should not be called"

    monkeypatch.setattr(app_module, "filter_message", fake_filter)

    response = client.post("/whatsapp", data={"Body": "hi", "From": "whatsapp:+19999999999"})

    assert response.status_code == 403
    assert calls == []


def test_returns_filtered_text(client, monkeypatch):
    async def fake_filter(text):
        return "FACTS:\n- Pickup at 5:30"

    monkeypatch.setattr(app_module, "filter_message", fake_filter)

    response = client.post(
        "/whatsapp",
        data={"Body": "You're so selfish. Pickup at 5:30.", "From": MY_NUMBER},
    )

    assert response.status_code == 200
    assert "Pickup at 5:30" in response.text
    assert "selfish" not in response.text


def test_never_shows_original_when_filter_fails(client, monkeypatch):
    async def broken_filter(text):
        raise RuntimeError("API is down")

    monkeypatch.setattr(app_module, "filter_message", broken_filter)

    response = client.post(
        "/whatsapp",
        data={"Body": "You're so selfish. Pickup at 5:30.", "From": MY_NUMBER},
    )

    assert response.status_code == 200
    assert "filter that message" in response.text
    assert "selfish" not in response.text