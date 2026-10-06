import asyncio
import logging

from message_filter.archive import archive_message
from message_filter.check import check_summary
from message_filter.filter import filter_message
from message_filter.formatting import (
    format_drafts_note,
    format_for_whatsapp,
    format_problems,
)
from message_filter.jobs import Job
from message_filter.models import CheckResult, FilteredMessage, ReplyDrafts
from message_filter.reply import draft_replies
from message_filter.sender import send_messages

logger = logging.getLogger(__name__)


async def safe_archive(message_sid: str, sender: str, body: str) -> None:
    try:
        await archive_message(message_sid, sender, body)
    except Exception:
        logger.exception("Archiving failed")


async def safe_check(text: str, result: FilteredMessage) -> CheckResult | None:
    try:
        return await check_summary(text, result)
    except Exception:
        logger.exception("Checking failed")
        return None


async def safe_drafts(result: FilteredMessage) -> ReplyDrafts | None:
    if not result.needs_reply:
        return None
    try:
        return await draft_replies(result)
    except Exception:
        logger.exception("Drafting replies failed")
        return None


async def build_reply(body: str) -> list[str]:
    try:
        result = await filter_message(body)
        summary = format_for_whatsapp(result)
    except Exception:
        logger.exception("Filtering failed")
        return ["Sorry, I couldn't filter that message. Please try again in a minute."]

    check, drafts = await asyncio.gather(safe_check(body, result), safe_drafts(result))

    parts = []
    if check is None:
        parts.append("NOTE: I couldn't double-check this summary.")
    elif check.problems:
        parts.append(format_problems(check))
    parts.append(summary)

    draft_texts = []
    if drafts is not None:
        parts.append(format_drafts_note(drafts))
        draft_texts = [option.text for option in drafts.options]
    elif result.needs_reply:
        parts.append("I couldn't draft replies this time.")

    return ["\n\n".join(parts)] + draft_texts


async def process_job(job: Job) -> None:
    logger.info("Processing %s", job.message_sid)
    await safe_archive(job.message_sid, job.recipient, job.body)
    texts = await build_reply(job.body)
    await send_messages(job.sandbox_number, job.recipient, texts)