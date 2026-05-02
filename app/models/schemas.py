"""Pydantic schemas used for request/response validation."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.models import TransactionStatus, TransactionType


# ── User ──────────────────────────────────────────────────────────────────────

class UserBase(BaseModel):
    phone_number: str
    business_name: str


class UserCreate(UserBase):
    pass


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


# ── Customer ──────────────────────────────────────────────────────────────────

class CustomerBase(BaseModel):
    name: str
    phone_number: Optional[str] = None


class CustomerCreate(CustomerBase):
    user_id: int


class CustomerRead(CustomerBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    total_debt: Decimal
    created_at: datetime


# ── Transaction ───────────────────────────────────────────────────────────────

class TransactionBase(BaseModel):
    transaction_type: TransactionType
    item_description: Optional[str] = None
    quantity: Optional[Decimal] = None
    unit: Optional[str] = None
    amount: Decimal
    raw_message: Optional[str] = None


class TransactionCreate(TransactionBase):
    customer_id: int


class TransactionRead(TransactionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    status: TransactionStatus
    mpesa_reference: Optional[str] = None
    created_at: datetime
