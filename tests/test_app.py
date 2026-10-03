import pytest
from fastapi.testclient import TestClient
from twilio.request_validator import RequestValidator

import message_filter.app as app_module
from message_filter.models import FilteredMessage

MY_NUMBER = "whatsapp:+15550001111"
TEST_TOKEN = "test-auth-token"
TEST_URL = "https://example.test/whatsapp"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(app_module, "ALLOWED_SENDER", MY_NUMBER)
    monkeypatch.setattr(app_module, "TWILIO_AUTH_TOKEN", TEST_TOKEN)
    monkeypatch.setattr(app_module, "PUBLIC_WEBHOOK_URL", TEST_URL)
    return TestClient(app_module.app)


@pytest.fixture
def filter_calls(monkeypatch):
    calls = []

    async def fake_filter(text):
        calls.append(text)
        return FilteredMessage(
            facts=["Pickup at 5:30"], needs_reply=False, questions=[], notes=[]
        )

    monkeypatch.setattr(app_module, "filter_message", fake_filter)
    return calls


def signed_post(client, data):
    signature = RequestValidator(TEST_TOKEN).compute_signature(TEST_URL, data)
    return client.post("/whatsapp", data=data, headers={"X-Twilio-Signature": signature})


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_rejects_missing_signature(client, filter_calls):
    response = client.post("/whatsapp", data={"Body": "hi", "From": MY_NUMBER})

    assert response.status_code == 403
    assert filter_calls == []


def test_rejects_wrong_signature(client, filter_calls):
    response = client.post(
        "/whatsapp",
        data={"Body": "hi", "From": MY_NUMBER},
        headers={"X-Twilio-Signature": "not-a-real-signature"},
    )

    assert response.status_code == 403
    assert filter_calls == []


def test_rejects_unknown_sender(client, filter_calls):
    response = signed_post(client, {"Body": "hi", "From": "whatsapp:+19999999999"})

    assert response.status_code == 403
    assert filter_calls == []


def test_returns_filtered_text(client, filter_calls):
    response = signed_post(
        client, {"Body": "You're so selfish. Pickup at 5:30.", "From": MY_NUMBER}
    )

    assert response.status_code == 200
    assert "Pickup at 5:30" in response.text
    assert "selfish" not in response.text


def test_never_shows_original_when_filter_fails(client, monkeypatch):
    async def broken_filter(text):
        raise RuntimeError("API is down")

    monkeypatch.setattr(app_module, "filter_message", broken_filter)

    response = signed_post(
        client, {"Body": "You're so selfish. Pickup at 5:30.", "From": MY_NUMBER}
    )

    assert response.status_code == 200
    assert "filter that message" in response.text
    assert "selfish" not in response.text