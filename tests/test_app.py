import pytest
from fastapi.testclient import TestClient
from twilio.request_validator import RequestValidator

import message_filter.app as app_module
from message_filter.models import (
    CheckResult,
    FilteredMessage,
    Problem,
    ReplyDrafts,
    ReplyOption,
)

MY_NUMBER = "whatsapp:+15550001111"
SANDBOX_NUMBER = "whatsapp:+14155238886"
TEST_TOKEN = "test-auth-token"
TEST_URL = "https://example.test/whatsapp"

NEEDS_REPLY = FilteredMessage(
    facts=["Request to switch weekends"],
    needs_reply=True,
    questions=["Can you take Sam on the 17th?"],
    notes=[],
)

FOUND_PROBLEM = CheckResult(
    problems=[Problem(kind="incorrect", description="The pickup time may be wrong.")]
)

TWO_DRAFTS = ReplyDrafts(
    options=[
        ReplyOption(label="Agree", text="Yes, I can take Sam on the 17th."),
        ReplyOption(label="Decline", text="I am not able to switch that weekend."),
    ]
)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(app_module, "ALLOWED_SENDER", MY_NUMBER)
    monkeypatch.setattr(app_module, "TWILIO_AUTH_TOKEN", TEST_TOKEN)
    monkeypatch.setattr(app_module, "PUBLIC_WEBHOOK_URL", TEST_URL)
    return TestClient(app_module.app)


@pytest.fixture(autouse=True)
def sent(monkeypatch):
    texts_sent = []

    async def fake_send(from_number, to_number, texts):
        texts_sent.extend(texts)

    monkeypatch.setattr(app_module, "send_messages", fake_send)
    return texts_sent


@pytest.fixture(autouse=True)
def archived(monkeypatch):
    records = []

    async def fake_archive(message_sid, sender, body):
        records.append((message_sid, sender, body))

    monkeypatch.setattr(app_module, "archive_message", fake_archive)
    return records


@pytest.fixture(autouse=True)
def check_finds_nothing(monkeypatch):
    async def fake_check(text, filtered):
        return CheckResult(problems=[])

    monkeypatch.setattr(app_module, "check_summary", fake_check)


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


@pytest.fixture
def filter_needs_reply(monkeypatch):
    async def fake_filter(text):
        return NEEDS_REPLY

    monkeypatch.setattr(app_module, "filter_message", fake_filter)


def signed_post(client, data):
    data = {"To": SANDBOX_NUMBER, "MessageSid": "SMtest", **data}
    signature = RequestValidator(TEST_TOKEN).compute_signature(TEST_URL, data)
    return client.post("/whatsapp", data=data, headers={"X-Twilio-Signature": signature})


def post_message(client, body="anything"):
    return signed_post(client, {"Body": body, "From": MY_NUMBER})


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_rejects_missing_signature(client, filter_calls, sent):
    response = client.post("/whatsapp", data={"Body": "hi", "From": MY_NUMBER})

    assert response.status_code == 403
    assert filter_calls == []
    assert sent == []


def test_rejects_wrong_signature(client, filter_calls, sent):
    response = client.post(
        "/whatsapp",
        data={"Body": "hi", "From": MY_NUMBER},
        headers={"X-Twilio-Signature": "not-a-real-signature"},
    )

    assert response.status_code == 403
    assert filter_calls == []
    assert sent == []


def test_rejects_unknown_sender(client, filter_calls, sent):
    response = signed_post(client, {"Body": "hi", "From": "whatsapp:+19999999999"})

    assert response.status_code == 403
    assert filter_calls == []
    assert sent == []


def test_answers_twilio_with_an_empty_response(client, filter_calls):
    response = post_message(client)

    assert response.status_code == 200
    assert "<Message>" not in response.text


def test_sends_filtered_text(client, filter_calls, sent):
    post_message(client, "You're so selfish. Pickup at 5:30.")

    assert len(sent) == 1
    assert "Pickup at 5:30" in sent[0]
    assert "selfish" not in sent[0]


def test_never_shows_original_when_filter_fails(client, sent, monkeypatch):
    async def broken_filter(text):
        raise RuntimeError("API is down")

    monkeypatch.setattr(app_module, "filter_message", broken_filter)

    post_message(client, "You're so selfish. Pickup at 5:30.")

    assert len(sent) == 1
    assert "filter that message" in sent[0]
    assert "selfish" not in sent[0]


def test_sends_each_draft_as_its_own_message(client, filter_needs_reply, sent, monkeypatch):
    async def fake_drafts(filtered):
        return TWO_DRAFTS

    monkeypatch.setattr(app_module, "draft_replies", fake_drafts)

    post_message(client)

    assert len(sent) == 3
    assert "DRAFT REPLIES (Agree, Decline)" in sent[0]
    assert sent[1] == "Yes, I can take Sam on the 17th."
    assert sent[2] == "I am not able to switch that weekend."


def test_skips_drafts_when_no_reply_needed(client, filter_calls, sent, monkeypatch):
    draft_calls = []

    async def fake_drafts(filtered):
        draft_calls.append(filtered)
        return ReplyDrafts(options=[])

    monkeypatch.setattr(app_module, "draft_replies", fake_drafts)

    post_message(client)

    assert len(sent) == 1
    assert draft_calls == []


def test_still_sends_facts_when_drafting_fails(client, filter_needs_reply, sent, monkeypatch):
    async def broken_drafts(filtered):
        raise RuntimeError("API is down")

    monkeypatch.setattr(app_module, "draft_replies", broken_drafts)

    post_message(client)

    assert len(sent) == 1
    assert "Request to switch weekends" in sent[0]
    assert "draft replies this time" in sent[0]


def test_puts_warning_above_facts(client, filter_calls, sent, monkeypatch):
    async def fake_check(text, filtered):
        return FOUND_PROBLEM

    monkeypatch.setattr(app_module, "check_summary", fake_check)

    post_message(client)

    assert "May be wrong: The pickup time may be wrong." in sent[0]
    assert sent[0].index("WARNING") < sent[0].index("FACTS")


def test_says_so_when_check_fails(client, filter_calls, sent, monkeypatch):
    async def broken_check(text, filtered):
        raise RuntimeError("API is down")

    monkeypatch.setattr(app_module, "check_summary", broken_check)

    post_message(client)

    assert "double-check this summary" in sent[0]
    assert "Pickup at 5:30" in sent[0]


def test_still_sends_drafts_when_check_finds_problems(
    client, filter_needs_reply, sent, monkeypatch
):
    async def fake_check(text, filtered):
        return FOUND_PROBLEM

    async def fake_drafts(filtered):
        return TWO_DRAFTS

    monkeypatch.setattr(app_module, "check_summary", fake_check)
    monkeypatch.setattr(app_module, "draft_replies", fake_drafts)

    post_message(client)

    assert "WARNING" in sent[0]
    assert len(sent) == 3


def test_replies_from_the_sandbox_number_to_the_sender(client, filter_calls, monkeypatch):
    addresses = []

    async def fake_send(from_number, to_number, texts):
        addresses.append((from_number, to_number))

    monkeypatch.setattr(app_module, "send_messages", fake_send)

    post_message(client)

    assert addresses == [(SANDBOX_NUMBER, MY_NUMBER)]


def test_survives_a_failed_send(client, filter_calls, monkeypatch):
    async def broken_send(from_number, to_number, texts):
        raise RuntimeError("Twilio is down")

    monkeypatch.setattr(app_module, "send_messages", broken_send)

    response = post_message(client)

    assert response.status_code == 200


def test_archives_the_original_untouched(client, filter_calls, archived):
    post_message(client, "You're so selfish. Pickup at 5:30.")

    assert archived == [("SMtest", MY_NUMBER, "You're so selfish. Pickup at 5:30.")]


def test_archives_before_filtering(client, monkeypatch):
    events = []

    async def fake_archive(message_sid, sender, body):
        events.append("archive")

    async def fake_filter(text):
        events.append("filter")
        return FilteredMessage(facts=[], needs_reply=False, questions=[], notes=[])

    monkeypatch.setattr(app_module, "archive_message", fake_archive)
    monkeypatch.setattr(app_module, "filter_message", fake_filter)

    post_message(client)

    assert events == ["archive", "filter"]


def test_still_replies_when_archiving_fails(client, filter_calls, sent, monkeypatch):
    async def broken_archive(message_sid, sender, body):
        raise RuntimeError("S3 is down")

    monkeypatch.setattr(app_module, "archive_message", broken_archive)

    post_message(client)

    assert len(sent) == 1
    assert "Pickup at 5:30" in sent[0]


def test_rejects_everything_when_no_sender_is_configured(client, filter_calls, monkeypatch):
    monkeypatch.setattr(app_module, "ALLOWED_SENDER", "")

    response = signed_post(client, {"Body": "hi"})

    assert response.status_code == 403
    assert filter_calls == []