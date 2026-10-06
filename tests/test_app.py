import pytest
from fastapi.testclient import TestClient
from twilio.request_validator import RequestValidator

import message_filter.app as app_module
from message_filter.jobs import Job

MY_NUMBER = "whatsapp:+15550001111"
SANDBOX_NUMBER = "whatsapp:+14155238886"
TEST_TOKEN = "test-auth-token"
TEST_URL = "https://example.test/whatsapp"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(app_module, "ALLOWED_SENDER", MY_NUMBER)
    monkeypatch.setattr(app_module, "TWILIO_AUTH_TOKEN", TEST_TOKEN)
    monkeypatch.setattr(app_module, "PUBLIC_WEBHOOK_URL", TEST_URL)
    return TestClient(app_module.app)


@pytest.fixture(autouse=True)
def queued(monkeypatch):
    jobs = []

    async def fake_enqueue(job):
        jobs.append(job)

    monkeypatch.setattr(app_module, "enqueue", fake_enqueue)
    return jobs


def signed_post(client, data):
    data = {"To": SANDBOX_NUMBER, "MessageSid": "SMtest", **data}
    signature = RequestValidator(TEST_TOKEN).compute_signature(TEST_URL, data)
    return client.post("/whatsapp", data=data, headers={"X-Twilio-Signature": signature})


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_rejects_missing_signature(client, queued):
    response = client.post("/whatsapp", data={"Body": "hi", "From": MY_NUMBER})

    assert response.status_code == 403
    assert queued == []


def test_rejects_wrong_signature(client, queued):
    response = client.post(
        "/whatsapp",
        data={"Body": "hi", "From": MY_NUMBER},
        headers={"X-Twilio-Signature": "not-a-real-signature"},
    )

    assert response.status_code == 403
    assert queued == []


def test_rejects_unknown_sender(client, queued):
    response = signed_post(client, {"Body": "hi", "From": "whatsapp:+19999999999"})

    assert response.status_code == 403
    assert queued == []


def test_rejects_everything_when_no_sender_is_configured(client, queued, monkeypatch):
    monkeypatch.setattr(app_module, "ALLOWED_SENDER", "")

    response = signed_post(client, {"Body": "hi"})

    assert response.status_code == 403
    assert queued == []


def test_queues_the_message_as_a_job(client, queued):
    signed_post(client, {"Body": "You're so selfish. Pickup at 5:30.", "From": MY_NUMBER})

    assert queued == [
        Job(
            message_sid="SMtest",
            body="You're so selfish. Pickup at 5:30.",
            recipient=MY_NUMBER,
            sandbox_number=SANDBOX_NUMBER,
        )
    ]


def test_answers_twilio_with_an_empty_response(client):
    response = signed_post(client, {"Body": "hi", "From": MY_NUMBER})

    assert response.status_code == 200
    assert "<Message>" not in response.text


def test_tells_you_when_the_message_cannot_be_queued(client, monkeypatch):
    async def broken_enqueue(job):
        raise RuntimeError("SQS is down")

    monkeypatch.setattr(app_module, "enqueue", broken_enqueue)

    response = signed_post(client, {"Body": "hi", "From": MY_NUMBER})

    assert response.status_code == 200
    assert "forward it again" in response.text