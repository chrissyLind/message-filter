import asyncio

import pytest

import message_filter.worker as worker
from message_filter.jobs import Job

JOB = Job(
    message_sid="SMtest",
    body="Pickup at 5:30",
    recipient="whatsapp:+15550001111",
    sandbox_number="whatsapp:+14155238886",
)


@pytest.fixture
def deleted(monkeypatch):
    handles = []

    async def fake_delete(receipt_handle):
        handles.append(receipt_handle)

    monkeypatch.setattr(worker, "delete", fake_delete)
    return handles


def queue_returns(monkeypatch, value):
    async def fake_receive():
        return value

    monkeypatch.setattr(worker, "receive", fake_receive)


def test_deletes_the_job_after_processing_it(deleted, monkeypatch):
    processed = []

    async def fake_process(job):
        processed.append(job)

    queue_returns(monkeypatch, (JOB, "handle-1"))
    monkeypatch.setattr(worker, "process_job", fake_process)

    asyncio.run(worker.handle_next_job())

    assert processed == [JOB]
    assert deleted == ["handle-1"]


def test_keeps_the_job_when_processing_fails(deleted, monkeypatch):
    async def broken_process(job):
        raise RuntimeError("Twilio is down")

    queue_returns(monkeypatch, (JOB, "handle-1"))
    monkeypatch.setattr(worker, "process_job", broken_process)

    asyncio.run(worker.handle_next_job())

    assert deleted == []


def test_does_nothing_when_the_queue_is_empty(deleted, monkeypatch):
    queue_returns(monkeypatch, None)

    asyncio.run(worker.handle_next_job())

    assert deleted == []