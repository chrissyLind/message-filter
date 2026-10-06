import asyncio

import pytest

import message_filter.pipeline as pipeline
from message_filter.jobs import Job
from message_filter.models import (
    CheckResult,
    FilteredMessage,
    Problem,
    ReplyDrafts,
    ReplyOption,
)

MY_NUMBER = "whatsapp:+15550001111"
SANDBOX_NUMBER = "whatsapp:+14155238886"

NO_REPLY = FilteredMessage(
    facts=["Pickup at 5:30"], needs_reply=False, questions=[], notes=[]
)
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


def run(body="anything"):
    job = Job(
        message_sid="SMtest", body=body, recipient=MY_NUMBER, sandbox_number=SANDBOX_NUMBER
    )
    asyncio.run(pipeline.process_job(job))


def returning(value):
    async def fake(*args):
        return value

    return fake


def failing(message="API is down"):
    async def fake(*args):
        raise RuntimeError(message)

    return fake


@pytest.fixture(autouse=True)
def sent(monkeypatch):
    texts_sent = []

    async def fake_send(from_number, to_number, texts):
        texts_sent.extend(texts)

    monkeypatch.setattr(pipeline, "send_messages", fake_send)
    return texts_sent


@pytest.fixture(autouse=True)
def archived(monkeypatch):
    records = []

    async def fake_archive(message_sid, sender, body):
        records.append((message_sid, sender, body))

    monkeypatch.setattr(pipeline, "archive_message", fake_archive)
    return records


@pytest.fixture(autouse=True)
def agents(monkeypatch):
    monkeypatch.setattr(pipeline, "filter_message", returning(NO_REPLY))
    monkeypatch.setattr(pipeline, "check_summary", returning(CheckResult(problems=[])))
    monkeypatch.setattr(pipeline, "draft_replies", returning(TWO_DRAFTS))


def test_sends_filtered_text(sent):
    run("You're so selfish. Pickup at 5:30.")

    assert len(sent) == 1
    assert "Pickup at 5:30" in sent[0]
    assert "selfish" not in sent[0]


def test_never_shows_original_when_filter_fails(sent, monkeypatch):
    monkeypatch.setattr(pipeline, "filter_message", failing())

    run("You're so selfish. Pickup at 5:30.")

    assert len(sent) == 1
    assert "filter that message" in sent[0]
    assert "selfish" not in sent[0]


def test_sends_each_draft_as_its_own_message(sent, monkeypatch):
    monkeypatch.setattr(pipeline, "filter_message", returning(NEEDS_REPLY))

    run()

    assert len(sent) == 3
    assert "DRAFT REPLIES (Agree, Decline)" in sent[0]
    assert sent[1] == "Yes, I can take Sam on the 17th."
    assert sent[2] == "I am not able to switch that weekend."


def test_skips_drafts_when_no_reply_needed(sent, monkeypatch):
    draft_calls = []

    async def fake_drafts(filtered):
        draft_calls.append(filtered)
        return TWO_DRAFTS

    monkeypatch.setattr(pipeline, "draft_replies", fake_drafts)

    run()

    assert len(sent) == 1
    assert draft_calls == []


def test_still_sends_facts_when_drafting_fails(sent, monkeypatch):
    monkeypatch.setattr(pipeline, "filter_message", returning(NEEDS_REPLY))
    monkeypatch.setattr(pipeline, "draft_replies", failing())

    run()

    assert len(sent) == 1
    assert "Request to switch weekends" in sent[0]
    assert "draft replies this time" in sent[0]


def test_puts_warning_above_facts(sent, monkeypatch):
    monkeypatch.setattr(pipeline, "check_summary", returning(FOUND_PROBLEM))

    run()

    assert "May be wrong: The pickup time may be wrong." in sent[0]
    assert sent[0].index("WARNING") < sent[0].index("FACTS")


def test_says_so_when_check_fails(sent, monkeypatch):
    monkeypatch.setattr(pipeline, "check_summary", failing())

    run()

    assert "double-check this summary" in sent[0]
    assert "Pickup at 5:30" in sent[0]


def test_still_sends_drafts_when_check_finds_problems(sent, monkeypatch):
    monkeypatch.setattr(pipeline, "filter_message", returning(NEEDS_REPLY))
    monkeypatch.setattr(pipeline, "check_summary", returning(FOUND_PROBLEM))

    run()

    assert "WARNING" in sent[0]
    assert len(sent) == 3


def test_sends_from_the_sandbox_number_to_the_recipient(monkeypatch):
    addresses = []

    async def fake_send(from_number, to_number, texts):
        addresses.append((from_number, to_number))

    monkeypatch.setattr(pipeline, "send_messages", fake_send)

    run()

    assert addresses == [(SANDBOX_NUMBER, MY_NUMBER)]


def test_archives_the_original_untouched(archived):
    run("You're so selfish. Pickup at 5:30.")

    assert archived == [("SMtest", MY_NUMBER, "You're so selfish. Pickup at 5:30.")]


def test_archives_before_filtering(monkeypatch):
    events = []

    async def fake_archive(message_sid, sender, body):
        events.append("archive")

    async def fake_filter(text):
        events.append("filter")
        return NO_REPLY

    monkeypatch.setattr(pipeline, "archive_message", fake_archive)
    monkeypatch.setattr(pipeline, "filter_message", fake_filter)

    run()

    assert events == ["archive", "filter"]


def test_still_replies_when_archiving_fails(sent, monkeypatch):
    monkeypatch.setattr(pipeline, "archive_message", failing("S3 is down"))

    run()

    assert len(sent) == 1
    assert "Pickup at 5:30" in sent[0]


def test_raises_when_sending_fails(monkeypatch):
    monkeypatch.setattr(pipeline, "send_messages", failing("Twilio is down"))

    with pytest.raises(RuntimeError):
        run()