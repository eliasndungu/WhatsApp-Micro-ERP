"""Tests for the message parser utility."""

import pytest

from app.utils.message_parser import ParsedTransaction, parse_message


class TestCreditMessages:
    def test_basic_credit(self):
        result = parse_message("Njoroge bought 2kg sugar for 400 on credit")
        assert result is not None
        assert result.customer_name == "Njoroge"
        assert result.transaction_type == "credit"
        assert result.amount == 400.0
        assert result.quantity == 2.0
        assert result.unit == "kg"
        assert result.item_description == "sugar"

    def test_credit_multi_word_item(self):
        result = parse_message("Wanjiku bought 1 loaf of bread for 60 on credit")
        assert result is not None
        assert result.transaction_type == "credit"
        assert result.amount == 60.0

    def test_credit_without_on_credit_suffix(self):
        result = parse_message("Kamau bought 5kg flour for 250")
        assert result is not None
        assert result.transaction_type == "credit"
        assert result.amount == 250.0
        assert result.quantity == 5.0

    def test_credit_case_insensitive(self):
        result = parse_message("NJOROGE BOUGHT 2KG SUGAR FOR 400 ON CREDIT")
        assert result is not None
        assert result.customer_name == "Njoroge"
        assert result.amount == 400.0

    def test_credit_decimal_amount(self):
        result = parse_message("Achieng bought 0.5kg butter for 85.50 on credit")
        assert result is not None
        assert result.amount == 85.50
        assert result.quantity == 0.5

    def test_credit_name_title_cased(self):
        result = parse_message("john doe bought 3kg rice for 180 on credit")
        assert result is not None
        assert result.customer_name == "John Doe"


class TestPaymentMessages:
    def test_simple_payment(self):
        result = parse_message("Akinyi paid 500")
        assert result is not None
        assert result.customer_name == "Akinyi"
        assert result.transaction_type == "payment"
        assert result.amount == 500.0
        assert result.mpesa_reference is None

    def test_payment_with_mpesa_ref(self):
        result = parse_message("Njoroge paid 400 via mpesa QHX4T5")
        assert result is not None
        assert result.transaction_type == "payment"
        assert result.amount == 400.0
        assert result.mpesa_reference == "QHX4T5"

    def test_payment_decimal_amount(self):
        result = parse_message("Kamau paid 1250.75")
        assert result is not None
        assert result.amount == 1250.75


class TestCashMessages:
    def test_basic_cash(self):
        result = parse_message("Record 3kg maize for 150 cash from Kamau")
        assert result is not None
        assert result.customer_name == "Kamau"
        assert result.transaction_type == "cash"
        assert result.amount == 150.0
        assert result.quantity == 3.0
        assert result.unit == "kg"
        assert result.item_description == "maize"

    def test_cash_case_insensitive(self):
        result = parse_message("RECORD 2KG SUGAR FOR 100 CASH FROM JANE")
        assert result is not None
        assert result.customer_name == "Jane"
        assert result.amount == 100.0


class TestUnrecognisedMessages:
    def test_random_text_returns_none(self):
        assert parse_message("Hello, how are you?") is None

    def test_empty_string_returns_none(self):
        assert parse_message("") is None

    def test_partial_match_returns_none(self):
        assert parse_message("bought sugar") is None
