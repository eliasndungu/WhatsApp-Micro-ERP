"""Message parser utility.

Parses natural-language WhatsApp messages sent by Kenyan shopkeepers into
structured transaction data.

Supported sentence patterns
----------------------------
* "<Name> bought <qty><unit> <item> for <amount> on credit"
* "<Name> paid <amount>"
* "<Name> paid <amount> via mpesa <ref>"
* "Record <qty><unit> <item> for <amount> cash from <Name>"

All matching is case-insensitive.
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ParsedTransaction:
    customer_name: str
    transaction_type: str        # "credit" | "payment" | "cash"
    amount: float
    item_description: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    mpesa_reference: Optional[str] = None


# ── Compiled patterns ──────────────────────────────────────────────────────────

# "Njoroge bought 2kg sugar for 400 on credit"
_CREDIT_PATTERN = re.compile(
    r"^(?P<name>[A-Za-z]+(?:\s[A-Za-z]+)*)\s+"
    r"bought\s+"
    r"(?:(?P<qty>\d+(?:\.\d+)?)\s*(?P<unit>[a-zA-Z]+)\s+)?"
    r"(?P<item>.+?)\s+"
    r"for\s+(?P<amount>\d+(?:\.\d+)?)"
    r"(?:\s+on\s+credit)?",
    re.IGNORECASE,
)

# "Akinyi paid 500" or "Akinyi paid 500 via mpesa QHX4T5"
_PAYMENT_PATTERN = re.compile(
    r"^(?P<name>[A-Za-z]+(?:\s[A-Za-z]+)*)\s+"
    r"paid\s+(?P<amount>\d+(?:\.\d+)?)"
    r"(?:\s+via\s+mpesa\s+(?P<ref>[A-Z0-9]+))?",
    re.IGNORECASE,
)

# "Record 3kg maize for 150 cash from Kamau"
_CASH_PATTERN = re.compile(
    r"^record\s+"
    r"(?:(?P<qty>\d+(?:\.\d+)?)\s*(?P<unit>[a-zA-Z]+)\s+)?"
    r"(?P<item>.+?)\s+"
    r"for\s+(?P<amount>\d+(?:\.\d+)?)\s+cash\s+from\s+"
    r"(?P<name>[A-Za-z]+(?:\s[A-Za-z]+)*)",
    re.IGNORECASE,
)

_PATTERNS = [
    ("credit", _CREDIT_PATTERN),
    ("payment", _PAYMENT_PATTERN),
    ("cash", _CASH_PATTERN),
]


def parse_message(text: str) -> Optional[ParsedTransaction]:
    """Parse a WhatsApp message and return a :class:`ParsedTransaction`.

    Returns ``None`` if the message does not match any known pattern.
    """
    text = text.strip()

    for txn_type, pattern in _PATTERNS:
        match = pattern.match(text)
        if match:
            groups = match.groupdict()
            qty_str = groups.get("qty")
            return ParsedTransaction(
                customer_name=_title_case(groups["name"]),
                transaction_type=txn_type,
                amount=float(groups["amount"]),
                item_description=groups.get("item"),
                quantity=float(qty_str) if qty_str else None,
                unit=groups.get("unit"),
                mpesa_reference=groups.get("ref"),
            )

    return None


def _title_case(name: str) -> str:
    return " ".join(word.capitalize() for word in name.split())
