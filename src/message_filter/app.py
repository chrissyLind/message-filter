from fastapi import FastAPI, Form
from fastapi.responses import Response
from twilio.twiml.messaging_response import MessagingResponse

app = FastAPI()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/whatsapp")
async def whatsapp_webhook(Body: str = Form(""), From: str = Form("")):
    reply = MessagingResponse()
    reply.message(f"Received {len(Body)} characters:\n\n{Body}")
    return Response(content=str(reply), media_type="application/xml")