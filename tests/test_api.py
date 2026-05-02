"""Integration tests for the webhook and M-Pesa endpoints using TestClient.

The tests use an in-memory SQLite database (configured in conftest.py) so
no running PostgreSQL is needed.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


class TestHealthEndpoint:
    def test_health_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestWebhookVerification:
    def test_valid_verify_token(self, client):
        response = client.get(
            "/webhook/",
            params={
                "hub.mode": "subscribe",
                "hub.challenge": "12345",
                "hub.verify_token": "my_verify_token",
            },
        )
        assert response.status_code == 200
        assert response.json() == 12345

    def test_invalid_verify_token(self, client):
        response = client.get(
            "/webhook/",
            params={
                "hub.mode": "subscribe",
                "hub.challenge": "12345",
                "hub.verify_token": "wrong_token",
            },
        )
        assert response.status_code == 403


class TestWebhookPost:
    def _make_payload(self, text: str, sender: str = "254700000000") -> dict:
        return {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "metadata": {"phone_number_id": "test_phone_id"},
                                "messages": [
                                    {
                                        "from": sender,
                                        "type": "text",
                                        "text": {"body": text},
                                    }
                                ],
                            }
                        }
                    ]
                }
            ]
        }

    def test_parseable_message_returns_ok(self, client):
        payload = self._make_payload("Njoroge bought 2kg sugar for 400 on credit")
        with patch(
            "app.routers.webhook.transaction_service.handle_parsed_transaction",
            new_callable=AsyncMock,
        ):
            response = client.post("/webhook/", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_unparseable_message_returns_ok(self, client):
        payload = self._make_payload("Hello world!")
        response = client.post("/webhook/", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_non_text_message_ignored(self, client):
        payload = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "metadata": {"phone_number_id": "test_phone_id"},
                                "messages": [{"from": "254700000000", "type": "image"}],
                            }
                        }
                    ]
                }
            ]
        }
        response = client.post("/webhook/", json=payload)
        assert response.status_code == 200

    def test_empty_payload_returns_ok(self, client):
        response = client.post("/webhook/", json={})
        assert response.status_code == 200


class TestMpesaCallback:
    def test_successful_callback(self, client):
        payload = {
            "Body": {
                "stkCallback": {
                    "ResultCode": 0,
                    "ResultDesc": "Success",
                    "CallbackMetadata": {
                        "Item": [
                            {"Name": "Amount", "Value": 400},
                            {"Name": "MpesaReceiptNumber", "Value": "QHX4T5ABC"},
                            {"Name": "PhoneNumber", "Value": 254712345678},
                            {"Name": "TransactionDate", "Value": "20240501120000"},
                        ]
                    },
                }
            }
        }
        with patch(
            "app.routers.mpesa.transaction_service.confirm_payment_by_mpesa",
            new_callable=AsyncMock,
        ):
            response = client.post("/mpesa/callback", json=payload)
        assert response.status_code == 200
        assert response.json()["ResultCode"] == 0

    def test_failed_callback(self, client):
        payload = {
            "Body": {
                "stkCallback": {
                    "ResultCode": 1032,
                    "ResultDesc": "Request cancelled by user",
                }
            }
        }
        response = client.post("/mpesa/callback", json=payload)
        assert response.status_code == 200
        assert response.json()["ResultCode"] == 0
