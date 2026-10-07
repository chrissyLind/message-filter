import asyncio

import fakeredis

from message_filter.dedupe import PROCESSING_SECONDS, claim, mark_done, release


def run(coroutine):
    return asyncio.run(coroutine)


def test_first_claim_is_new():
    assert run(claim("SM1")) == "new"


def test_second_claim_is_processing():
    run(claim("SM1"))
    assert run(claim("SM1")) == "processing"


def test_claim_after_done_is_done():
    run(claim("SM1"))
    run(mark_done("SM1"))
    assert run(claim("SM1")) == "done"


def test_claim_after_release_is_new_again():
    run(claim("SM1"))
    run(release("SM1"))
    assert run(claim("SM1")) == "new"


def test_claim_expires(fake_redis):
    run(claim("SM1"))
    redis = fakeredis.FakeRedis(server=fake_redis)
    assert 0 < redis.ttl("job:SM1") <= PROCESSING_SECONDS