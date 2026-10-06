import asyncio
import logging

from message_filter.jobs import delete, receive
from message_filter.pipeline import process_job

logger = logging.getLogger(__name__)


async def handle_next_job() -> None:
    received = await receive()
    if received is None:
        return
    job, receipt_handle = received
    try:
        await process_job(job)
    except Exception:
        logger.exception("Job failed and will be retried")
        return
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