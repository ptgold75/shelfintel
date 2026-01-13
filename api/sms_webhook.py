# api/sms_webhook.py
"""Twilio SMS webhook endpoint for receiving loyalty program messages."""

import os
import sys
from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.loyalty import store_sms_message, get_subscription_by_phone

app = FastAPI(title="CannLinx SMS Webhook")


@app.post("/api/sms/webhook")
async def receive_sms(request: Request):
    """
    Receive inbound SMS from Twilio.

    Twilio sends POST data with:
    - From: sender phone number
    - To: your Twilio phone number
    - Body: message text
    - MessageSid: unique message ID
    """
    try:
        form_data = await request.form()

        from_number = form_data.get("From", "")
        to_number = form_data.get("To", "")
        message_body = form_data.get("Body", "")
        message_sid = form_data.get("MessageSid", "")

        print(f"[SMS] Received from {from_number} to {to_number}: {message_body[:50]}...")

        # Find subscription by Twilio phone number
        subscription = get_subscription_by_phone(to_number)

        if subscription:
            # Store the message
            msg_id = store_sms_message(
                subscription_id=subscription["subscription_id"],
                from_number=from_number,
                to_number=to_number,
                message=message_body
            )
            print(f"[SMS] Stored message {msg_id} for {subscription['dispensary_name']}")
        else:
            print(f"[SMS] No subscription found for Twilio number {to_number}")

        # Return TwiML response (empty response = don't reply)
        twiml = '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'
        return Response(content=twiml, media_type="application/xml")

    except Exception as e:
        print(f"[SMS] Error processing message: {e}")
        # Still return valid TwiML to prevent Twilio errors
        twiml = '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'
        return Response(content=twiml, media_type="application/xml")


@app.get("/api/sms/status")
async def status():
    """Health check endpoint."""
    return {"status": "ok", "service": "CannLinx SMS Webhook"}


@app.post("/api/sms/test")
async def test_message(request: Request):
    """
    Test endpoint to simulate receiving an SMS.

    POST JSON: {
        "from_number": "+15551234567",
        "to_number": "+15559876543",
        "message": "30% off all flower today!"
    }
    """
    try:
        data = await request.json()

        from_number = data.get("from_number", "+15551234567")
        to_number = data.get("to_number")
        message = data.get("message", "Test message")

        if not to_number:
            return {"error": "to_number is required (your Twilio phone number)"}

        # Find subscription
        subscription = get_subscription_by_phone(to_number)

        if not subscription:
            return {"error": f"No subscription found for {to_number}"}

        # Store the message
        msg_id = store_sms_message(
            subscription_id=subscription["subscription_id"],
            from_number=from_number,
            to_number=to_number,
            message=message
        )

        return {
            "status": "success",
            "message_id": msg_id,
            "dispensary": subscription["dispensary_name"],
            "parsed": True
        }

    except Exception as e:
        return {"error": str(e)}


# Run with: uvicorn api.sms_webhook:app --host 0.0.0.0 --port 8000
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
