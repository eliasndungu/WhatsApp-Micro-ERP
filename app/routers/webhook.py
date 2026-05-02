"""WhatsApp Cloud API webhook router.

Handles:
* GET  /webhook  – verification challenge from Meta
* POST /webhook  – incoming message events
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.services import transaction_service
from app.utils.message_parser import parse_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["WhatsApp Webhook"])


# ── Verification (GET) ────────────────────────────────────────────────────────

@router.get("/", summary="Meta webhook verification challenge")
def verify_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_challenge: str = Query(alias="hub.challenge"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    settings: Settings = Depends(get_settings),
):
    """Respond to Meta's webhook verification handshake."""
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("Webhook verified successfully.")
        return int(hub_challenge)
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verification failed")


# ── Incoming messages (POST) ──────────────────────────────────────────────────

@router.post("/", status_code=status.HTTP_200_OK, summary="Receive WhatsApp message events")
async def receive_message(
    request: Request,
    db: Session = Depends(get_db),
):
    """Process an incoming WhatsApp Cloud API webhook payload."""
    payload: dict[str, Any] = await request.json()
    logger.debug("Received webhook payload: %s", payload)

    try:
        entries = payload.get("entry", [])
        for entry in entries:
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])
                metadata = value.get("metadata", {})
                phone_number_id = metadata.get("phone_number_id", "")

                for message in messages:
                    if message.get("type") != "text":
                        continue  # skip non-text messages for now

                    sender = message["from"]
                    text_body: str = message["text"]["body"]

                    logger.info("Message from %s: %s", sender, text_body)

                    parsed = parse_message(text_body)
                    if parsed is None:
                        logger.info("Message did not match any known pattern – skipping.")
                        continue

                    await transaction_service.handle_parsed_transaction(
                        db=db,
                        sender_phone=sender,
                        phone_number_id=phone_number_id,
                        parsed=parsed,
                        raw_message=text_body,
                    )
    except Exception:  # noqa: BLE001
        logger.exception("Unhandled error while processing webhook payload")
        # Always return 200 to prevent Meta from retrying infinitely.
        # Do not expose internal error details to the caller.
        return {"status": "error"}

    return {"status": "ok"}
