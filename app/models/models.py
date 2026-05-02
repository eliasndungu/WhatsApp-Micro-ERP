"""SQLAlchemy ORM models for the WhatsApp Micro ERP.

Tables
------
* users        – shopkeepers who own the WhatsApp number
* customers    – debtors / buyers associated with a shop
* transactions – individual credit/debit/payment events
"""

import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ── Enumerations ──────────────────────────────────────────────────────────────

class TransactionType(str, enum.Enum):
    CREDIT = "credit"       # goods given on credit
    PAYMENT = "payment"     # customer pays back debt
    CASH = "cash"           # immediate cash purchase


class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


# ── Models ────────────────────────────────────────────────────────────────────

class User(Base):
    """A shopkeeper / business owner who uses the ERP via WhatsApp."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    phone_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    business_name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    customers: Mapped[list["Customer"]] = relationship(
        "Customer", back_populates="user", cascade="all, delete-orphan"
    )


class Customer(Base):
    """A debtor / buyer who owes money to a shopkeeper."""

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    total_debt: Mapped[float] = mapped_column(
        Numeric(precision=14, scale=2), nullable=False, default=0.0
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="customers")
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="customer", cascade="all, delete-orphan"
    )


class Transaction(Base):
    """A single credit, payment, or cash-sale event."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    transaction_type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType), nullable=False
    )
    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus), nullable=False, default=TransactionStatus.PENDING
    )
    item_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity: Mapped[float | None] = mapped_column(
        Numeric(precision=10, scale=3), nullable=True
    )
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(precision=14, scale=2), nullable=False)
    # M-Pesa reference for confirmed payments
    mpesa_reference: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Raw WhatsApp message that triggered this transaction
    raw_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    customer: Mapped["Customer"] = relationship("Customer", back_populates="transactions")
