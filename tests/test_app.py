import pytest
from fastapi.testclient import TestClient
from twilio.request_validator import RequestValidator

import message_filter.app as app_module
from message_filter.models import FilteredMessage, ReplyDrafts, ReplyOption

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


NEEDS_REPLY = FilteredMessage(
    facts=["Request to switch weekends"],
    needs_reply=True,
    questions=["Can you take Sam on the 17th?"],
    notes=[],
)


@pytest.fixture
def filter_needs_reply(monkeypatch):
    async def fake_filter(text):
        return NEEDS_REPLY

    monkeypatch.setattr(app_module, "filter_message", fake_filter)


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


def test_sends_each_draft_as_its_own_message(client, filter_needs_reply, monkeypatch):
    async def fake_drafts(filtered):
        return ReplyDrafts(
            options=[
                ReplyOption(label="Agree", text="Yes, I can take Sam on the 17th."),
                ReplyOption(label="Decline", text="I am not able to switch that weekend."),
            ]
        )

    monkeypatch.setattr(app_module, "draft_replies", fake_drafts)

    response = signed_post(client, {"Body": "anything", "From": MY_NUMBER})

    assert response.status_code == 200
    assert response.text.count("<Message>") == 3
    assert "DRAFT REPLIES (Agree, Decline)" in response.text
    assert "<Message>Yes, I can take Sam on the 17th.</Message>" in response.text
    assert "<Message>I am not able to switch that weekend.</Message>" in response.text


def test_skips_drafts_when_no_reply_needed(client, filter_calls, monkeypatch):
    draft_calls = []

    async def fake_drafts(filtered):
        draft_calls.append(filtered)
        return ReplyDrafts(options=[])

    monkeypatch.setattr(app_module, "draft_replies", fake_drafts)

    response = signed_post(client, {"Body": "anything", "From": MY_NUMBER})

    assert response.text.count("<Message>") == 1
    assert draft_calls == []


def test_still_sends_facts_when_drafting_fails(client, filter_needs_reply, monkeypatch):
    async def broken_drafts(filtered):
        raise RuntimeError("API is down")

    monkeypatch.setattr(app_module, "draft_replies", broken_drafts)

    response = signed_post(client, {"Body": "anything", "From": MY_NUMBER})

    assert response.status_code == 200
    assert response.text.count("<Message>") == 1
    assert "Request to switch weekends" in response.text
    assert "draft replies this time" in response.text