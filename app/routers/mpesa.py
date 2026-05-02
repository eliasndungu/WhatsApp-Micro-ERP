"""M-Pesa / Daraja callback router.

Handles:
* POST /mpesa/callback  – STK Push result callback from Safaricom
"""

import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.daraja import parse_stk_callback
from app.services import transaction_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mpesa", tags=["M-Pesa"])


@router.post(
    "/callback",
    status_code=status.HTTP_200_OK,
    summary="Receive STK Push result from Safaricom Daraja",
)
async def mpesa_callback(payload: dict, db: Session = Depends(get_db)):
    """Handle M-Pesa STK Push callback and mark the related transaction."""
    logger.debug("M-Pesa callback payload: %s", payload)

    parsed = parse_stk_callback(payload)

    if parsed["result_code"] == 0 and parsed["mpesa_receipt"]:
        await transaction_service.confirm_payment_by_mpesa(
            db=db,
            mpesa_receipt=parsed["mpesa_receipt"],
            phone_number=parsed.get("phone_number"),
            amount=parsed.get("amount"),
        )
        logger.info("Payment confirmed: %s", parsed["mpesa_receipt"])
    else:
        logger.warning("M-Pesa callback – failed/cancelled: %s", parsed["result_desc"])

    # Safaricom requires a 200 response with specific JSON
    return {"ResultCode": 0, "ResultDesc": "Accepted"}
