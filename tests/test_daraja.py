"""Tests for the Daraja (M-Pesa) service helpers."""

import pytest

from app.services.daraja import parse_stk_callback


class TestParseStkCallback:
    def _make_payload(self, result_code: int, items: list) -> dict:
        return {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": "test-merchant",
                    "CheckoutRequestID": "test-checkout",
                    "ResultCode": result_code,
                    "ResultDesc": "The service request is processed successfully."
                    if result_code == 0
                    else "Request cancelled by user",
                    "CallbackMetadata": {"Item": items},
                }
            }
        }

    def test_successful_payment(self):
        payload = self._make_payload(
            0,
            [
                {"Name": "Amount", "Value": 400},
                {"Name": "MpesaReceiptNumber", "Value": "QHX4T5ABC"},
                {"Name": "PhoneNumber", "Value": 254712345678},
                {"Name": "TransactionDate", "Value": "20240501120000"},
            ],
        )
        result = parse_stk_callback(payload)
        assert result["result_code"] == 0
        assert result["mpesa_receipt"] == "QHX4T5ABC"
        assert result["amount"] == 400
        assert result["phone_number"] == "254712345678"
        assert result["transaction_date"] == "20240501120000"

    def test_cancelled_payment(self):
        payload = {
            "Body": {
                "stkCallback": {
                    "ResultCode": 1032,
                    "ResultDesc": "Request cancelled by user",
                }
            }
        }
        result = parse_stk_callback(payload)
        assert result["result_code"] == 1032
        assert result["mpesa_receipt"] is None
        assert result["amount"] is None

    def test_empty_payload(self):
        result = parse_stk_callback({})
        assert result["result_code"] is None
        assert result["mpesa_receipt"] is None
