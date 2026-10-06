import logging
import os

from fastapi import FastAPI, Request
from fastapi.responses import Response
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse

from message_filter.jobs import Job, enqueue

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


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    form = await request.form()
    params = {key: str(value) for key, value in form.items()}
    signature = request.headers.get("X-Twilio-Signature", "")

    if not is_from_twilio(params, signature):
        return Response(status_code=403)

    if not ALLOWED_SENDER or params.get("From") != ALLOWED_SENDER:
        return Response(status_code=403)

    job = Job(
        message_sid=params.get("MessageSid", "unknown"),
        body=params.get("Body", ""),
        recipient=params["From"],
        sandbox_number=params.get("To", ""),
    )

    reply = MessagingResponse()
    try:
        await enqueue(job)
    except Exception:
        logger.exception("Could not queue the message")
        reply.message("Sorry, I couldn't accept that message. Please forward it again.")

    return Response(content=str(reply), media_type="application/xml")