import asyncio
import logging
import os

from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.responses import Response
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse

from message_filter.check import check_summary
from message_filter.filter import filter_message
from message_filter.formatting import (
    format_drafts_note,
    format_for_whatsapp,
    format_problems,
)
from message_filter.models import CheckResult, FilteredMessage, ReplyDrafts
from message_filter.reply import draft_replies
from message_filter.sender import send_messages
from message_filter.archive import archive_message

logger = logging.getLogger(__name__)

app = FastAPI()

ALLOWED_SENDER = os.environ.get("ALLOWED_SENDER", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
PUBLIC_WEBHOOK_URL = os.environ.get("PUBLIC_WEBHOOK_URL", "")


def is_from_twilio(params: dict[str, str], signature: str) -> bool:
    if not TWILIO_AUTH_TOKEN or not PUBLIC_WEBHOOK_URL:
        return False
    validator = RequestValidator(TWILIO_AUTH_TOKEN)
    return validator.validate(PUBLIC_WEBHOOK_URL, params, signature)


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


async def safe_archive(message_sid: str, sender: str, body: str) -> None:
    try:
        await archive_message(message_sid, sender, body)
    except Exception:
        logger.exception("Archiving failed")


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


async def process_message(
    message_sid: str, body: str, recipient: str, sandbox_number: str
) -> None:
    await safe_archive(message_sid, recipient, body)
    texts = await build_reply(body)
    try:
        await send_messages(sandbox_number, recipient, texts)
    except Exception:
        logger.exception("Sending the reply failed")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/whatsapp")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    form = await request.form()
    params = {key: str(value) for key, value in form.items()}
    signature = request.headers.get("X-Twilio-Signature", "")

    if not is_from_twilio(params, signature):
        return Response(status_code=403)

    if not ALLOWED_SENDER or params.get("From") != ALLOWED_SENDER:
        return Response(status_code=403)

    background_tasks.add_task(
        process_message,
        params.get("MessageSid", "unknown"),
        params.get("Body", ""),
        params["From"],
        params.get("To", ""),
    )
    return Response(content=str(MessagingResponse()), media_type="application/xml")