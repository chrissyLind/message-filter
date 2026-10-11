import asyncio

import pytest

import message_filter.worker as worker
from message_filter.jobs import Job
from message_filter import dedupe
from message_filter.dedupe import claim

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


@pytest.fixture
def processed(monkeypatch):
    jobs = []

    async def fake_process(job):
        jobs.append(job)

    monkeypatch.setattr(worker, "process_job", fake_process)
    return jobs


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


def test_processes_a_duplicate_only_once(deleted, processed, monkeypatch):
    queue_returns(monkeypatch, (JOB, "handle-1"))
    asyncio.run(worker.handle_next_job())

    queue_returns(monkeypatch, (JOB, "handle-2"))
    asyncio.run(worker.handle_next_job())

    assert processed == [JOB]
    assert deleted == ["handle-1", "handle-2"]


def test_leaves_a_job_that_is_already_in_progress(deleted, processed, monkeypatch):
    asyncio.run(claim("SMtest"))
    queue_returns(monkeypatch, (JOB, "handle-1"))

    asyncio.run(worker.handle_next_job())

    assert processed == []
    assert deleted == []


def test_a_failed_job_can_be_claimed_again(deleted, monkeypatch):
    async def broken_process(job):
        raise RuntimeError("Twilio is down")

    queue_returns(monkeypatch, (JOB, "handle-1"))
    monkeypatch.setattr(worker, "process_job", broken_process)

    asyncio.run(worker.handle_next_job())

    assert asyncio.run(claim("SMtest")) == "new"


def test_processes_anyway_when_redis_is_down(deleted, processed, monkeypatch):
    def broken_client():
        raise ConnectionError("Redis is down")

    monkeypatch.setattr(dedupe, "get_client", broken_client)
    queue_returns(monkeypatch, (JOB, "handle-1"))

    asyncio.run(worker.handle_next_job())

    assert processed == [JOB]
    assert deleted == ["handle-1"]


def test_finishes_the_current_job_then_stops(monkeypatch):
    stopping = asyncio.Event()
    calls = []

    async def fake_handle_next_job():
        calls.append("job")
        if len(calls) == 2:
            stopping.set()

    monkeypatch.setattr(worker, "handle_next_job", fake_handle_next_job)

    asyncio.run(worker.run(stopping))

    assert calls == ["job", "job"]