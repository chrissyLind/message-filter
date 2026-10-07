import asyncio
import logging

from message_filter.jobs import delete, receive
from message_filter.pipeline import process_job

logger = logging.getLogger(__name__)


from message_filter.dedupe import claim, mark_done, release


async def safe_claim(message_sid: str) -> str:
    try:
        return await claim(message_sid)
    except Exception:
        logger.exception("Could not reach Redis; processing anyway")
        return "new"


async def safe_mark_done(message_sid: str) -> None:
    try:
        await mark_done(message_sid)
    except Exception:
        logger.exception("Could not record %s as done", message_sid)


async def safe_release(message_sid: str) -> None:
    try:
        await release(message_sid)
    except Exception:
        logger.exception("Could not release %s", message_sid)


async def handle_next_job() -> None:
    received = await receive()
    if received is None:
        return
    job, receipt_handle = received

    state = await safe_claim(job.message_sid)
    if state == "done":
        logger.info("Skipping %s: already handled", job.message_sid)
        await delete(receipt_handle)
        return
    if state == "processing":
        logger.info("Skipping %s: already in progress", job.message_sid)
        return

    try:
        await process_job(job)
    except Exception:
        logger.exception("Job failed and will be retried")
        await safe_release(job.message_sid)
        return
    await safe_mark_done(job.message_sid)
    await delete(receipt_handle)

async def main() -> None:
    logger.info("Worker started")
    while True:
        try:
            await handle_next_job()
        except Exception:
            logger.exception("Could not receive a job")
            await asyncio.sleep(5)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())