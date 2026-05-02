"""Business logic for creating and updating transactions.

This service is the single place that writes to the database.  The webhook
router and M-Pesa callback router both delegate here.
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.models import Customer, Transaction, TransactionStatus, TransactionType, User
from app.utils.message_parser import ParsedTransaction

logger = logging.getLogger(__name__)


# ── Helper: look up or create a User by phone ─────────────────────────────────

def _get_or_create_user(db: Session, phone_number: str) -> User:
    user = db.query(User).filter(User.phone_number == phone_number).first()
    if not user:
        user = User(phone_number=phone_number, business_name=f"Shop {phone_number}")
        db.add(user)
        db.flush()
    return user


def _get_or_create_customer(db: Session, user: User, customer_name: str) -> Customer:
    customer = (
        db.query(Customer)
        .filter(Customer.user_id == user.id, Customer.name == customer_name)
        .first()
    )
    if not customer:
        customer = Customer(user_id=user.id, name=customer_name, total_debt=0)
        db.add(customer)
        db.flush()
    return customer


# ── Main entry-point called by the webhook router ─────────────────────────────

async def handle_parsed_transaction(
    db: Session,
    sender_phone: str,
    phone_number_id: str,  # reserved for future use (send reply via WA API)
    parsed: ParsedTransaction,
    raw_message: str,
) -> Transaction:
    """Persist a parsed WhatsApp message as a transaction."""

    user = _get_or_create_user(db, sender_phone)
    customer = _get_or_create_customer(db, user, parsed.customer_name)

    txn_type = TransactionType(parsed.transaction_type)
    status = (
        TransactionStatus.CONFIRMED
        if txn_type == TransactionType.CASH
        else TransactionStatus.PENDING
    )

    transaction = Transaction(
        customer_id=customer.id,
        transaction_type=txn_type,
        status=status,
        item_description=parsed.item_description,
        quantity=parsed.quantity,
        unit=parsed.unit,
        amount=parsed.amount,
        mpesa_reference=parsed.mpesa_reference,
        raw_message=raw_message,
    )
    db.add(transaction)

    # Update running debt balance
    if txn_type == TransactionType.CREDIT:
        customer.total_debt = float(customer.total_debt) + parsed.amount
    elif txn_type == TransactionType.PAYMENT:
        customer.total_debt = max(0.0, float(customer.total_debt) - parsed.amount)

    db.commit()
    db.refresh(transaction)
    logger.info(
        "Transaction #%s created for customer '%s' (type=%s, amount=%.2f)",
        transaction.id,
        customer.name,
        txn_type.value,
        parsed.amount,
    )
    return transaction


# ── Called by the M-Pesa callback router ─────────────────────────────────────

async def confirm_payment_by_mpesa(
    db: Session,
    mpesa_receipt: str,
    phone_number: Optional[str],
    amount: Optional[float],
) -> Optional[Transaction]:
    """Mark the most recent pending payment transaction as CONFIRMED."""
    query = (
        db.query(Transaction)
        .filter(
            Transaction.transaction_type == TransactionType.PAYMENT,
            Transaction.status == TransactionStatus.PENDING,
        )
        .order_by(Transaction.created_at.desc())
    )

    # Narrow by amount when available
    if amount is not None:
        query = query.filter(Transaction.amount == amount)

    transaction = query.first()
    if not transaction:
        logger.warning(
            "No pending payment found to confirm (receipt=%s, amount=%s)",
            mpesa_receipt,
            amount,
        )
        return None

    transaction.status = TransactionStatus.CONFIRMED
    transaction.mpesa_reference = mpesa_receipt
    db.commit()
    db.refresh(transaction)
    logger.info("Transaction #%s confirmed via M-Pesa receipt %s", transaction.id, mpesa_receipt)
    return transaction
