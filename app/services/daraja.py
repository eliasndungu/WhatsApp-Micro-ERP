"""Daraja (Safaricom M-Pesa) API integration.

Exposes helpers for:
* Obtaining an OAuth access token
* Initiating an STK Push (Lipa Na M-Pesa Online)
* Parsing incoming C2B / STK-push callback payloads
"""

import base64
import logging
from datetime import datetime
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def get_access_token() -> str:
    """Fetch a short-lived OAuth 2.0 access token from Daraja."""
    credentials = f"{settings.DARAJA_CONSUMER_KEY}:{settings.DARAJA_CONSUMER_SECRET}"
    encoded = base64.b64encode(credentials.encode()).decode()

    url = f"{settings.DARAJA_BASE_URL}/oauth/v1/generate?grant_type=client_credentials"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers={"Authorization": f"Basic {encoded}"})
        response.raise_for_status()
        return response.json()["access_token"]


async def initiate_stk_push(
    phone_number: str,
    amount: int,
    account_reference: str,
    transaction_desc: str = "Debt Payment",
) -> dict[str, Any]:
    """Trigger an STK Push prompt on the customer's phone.

    Args:
        phone_number: Recipient phone in format ``2547XXXXXXXX``.
        amount: Amount in KES (must be a whole number).
        account_reference: Order/transaction reference shown to the customer.
        transaction_desc: Short description shown on the M-Pesa prompt.

    Returns:
        The raw Daraja API response dictionary.
    """
    access_token = await get_access_token()
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password_raw = f"{settings.DARAJA_SHORTCODE}{settings.DARAJA_PASSKEY}{timestamp}"
    password = base64.b64encode(password_raw.encode()).decode()

    payload = {
        "BusinessShortCode": settings.DARAJA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone_number,
        "PartyB": settings.DARAJA_SHORTCODE,
        "PhoneNumber": phone_number,
        "CallBackURL": settings.DARAJA_CALLBACK_URL,
        "AccountReference": account_reference,
        "TransactionDesc": transaction_desc,
    }

    url = f"{settings.DARAJA_BASE_URL}/mpesa/stkpush/v1/processrequest"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        return response.json()


def parse_stk_callback(payload: dict[str, Any]) -> dict[str, Any]:
    """Extract key fields from an STK Push callback payload.

    Returns a dict with keys: ``result_code``, ``result_desc``,
    ``mpesa_receipt``, ``amount``, ``phone_number``, ``transaction_date``.
    """
    body = payload.get("Body", {}).get("stkCallback", {})
    result_code = body.get("ResultCode")
    result_desc = body.get("ResultDesc", "")

    parsed: dict[str, Any] = {
        "result_code": result_code,
        "result_desc": result_desc,
        "mpesa_receipt": None,
        "amount": None,
        "phone_number": None,
        "transaction_date": None,
    }

    if result_code == 0:
        items = body.get("CallbackMetadata", {}).get("Item", [])
        for item in items:
            name = item.get("Name")
            value = item.get("Value")
            if name == "MpesaReceiptNumber":
                parsed["mpesa_receipt"] = value
            elif name == "Amount":
                parsed["amount"] = value
            elif name == "PhoneNumber":
                parsed["phone_number"] = str(value)
            elif name == "TransactionDate":
                parsed["transaction_date"] = str(value)

    return parsed
