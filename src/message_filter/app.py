import logging
import os

from fastapi import FastAPI, Form
from fastapi.responses import Response
from twilio.twiml.messaging_response import MessagingResponse

from message_filter.filter import filter_message

logger = logging.getLogger(__name__)
app = FastAPI()

ALLOWED_SENDER = os.environ.get("ALLOWED_SENDER", "")

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/whatsapp")
async def whatsapp_webhook(Body: str = Form(""), From: str = Form("")):
    if From != ALLOWED_SENDER:
        return Response(status_code=403)
    try:
        filtered = await filter_message(Body)
    except Exception:
        logger.exception("Filtering failed")
        filtered = "Sorry, I couldn't filter that message. Please try again in a minute."

    reply = MessagingResponse()
    reply.message(filtered)
    return Response(content=str(reply), media_type="application/xml")