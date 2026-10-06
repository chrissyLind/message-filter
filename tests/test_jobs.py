import asyncio
from types import SimpleNamespace

import message_filter.jobs as jobs
from message_filter.jobs import Job

JOB = Job(
    message_sid="SMtest",
    body="Pickup at 5:30",
    recipient="whatsapp:+15550001111",
    sandbox_number="whatsapp:+14155238886",
)


def use_fake_client(monkeypatch, **methods):
    monkeypatch.setattr(jobs, "get_client", lambda: SimpleNamespace(**methods))
    monkeypatch.setenv("QUEUE_URL", "https://example.test/queue")


def test_enqueue_sends_the_job_as_json(monkeypatch):
    calls = []
    use_fake_client(monkeypatch, send_message=lambda **kwargs: calls.append(kwargs))

    asyncio.run(jobs.enqueue(JOB))

    assert calls[0]["QueueUrl"] == "https://example.test/queue"
    assert Job.model_validate_json(calls[0]["MessageBody"]) == JOB


def test_receive_returns_the_job_and_its_handle(monkeypatch):
    response = {"Messages": [{"Body": JOB.model_dump_json(), "ReceiptHandle": "handle-1"}]}
    use_fake_client(monkeypatch, receive_message=lambda **kwargs: response)

    assert asyncio.run(jobs.receive()) == (JOB, "handle-1")


def test_receive_returns_none_when_the_queue_is_empty(monkeypatch):
    use_fake_client(monkeypatch, receive_message=lambda **kwargs: {})

    assert asyncio.run(jobs.receive()) is None


def test_delete_passes_the_receipt_handle(monkeypatch):
    calls = []
    use_fake_client(monkeypatch, delete_message=lambda **kwargs: calls.append(kwargs))

    asyncio.run(jobs.delete("handle-1"))

    assert calls[0]["ReceiptHandle"] == "handle-1"