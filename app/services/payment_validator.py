from typing import List
from decimal import Decimal
from rest_framework import status

from .fee_strategy import supported_payment_methods, get_fee_percentage


class PaymentValidationError(Exception):
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(message)
        self.status_code = status_code


def validate_currency(data: dict) -> None:
    if data.get("currency") != "BRL":
        raise PaymentValidationError("unsupported currency", status.HTTP_400_BAD_REQUEST)


def validate_payment_method(payment_method: str) -> None:
    if payment_method is None:
        raise PaymentValidationError("payment_method required", status.HTTP_400_BAD_REQUEST)
    if payment_method.lower() not in supported_payment_methods():
        raise PaymentValidationError("unsupported payment_method", status.HTTP_422_UNPROCESSABLE_ENTITY)


def validate_installments(payment_method: str, installments: int) -> None:
    pm = (payment_method or "").lower()
    if pm == "pix" and installments and installments > 1:
        raise PaymentValidationError("PIX does not accept installments", status.HTTP_400_BAD_REQUEST)
    if pm == "card":
        if not (1 <= installments <= 12):
            raise PaymentValidationError("card installments must be between 1 and 12", status.HTTP_400_BAD_REQUEST)


def validate_splits(splits: List[dict]) -> None:
    if not (1 <= len(splits) <= 5):
        raise PaymentValidationError("splits must be between 1 and 5", status.HTTP_400_BAD_REQUEST)
    total_pct = sum(s.get("percent", 0) for s in splits)
    if total_pct != 100:
        raise PaymentValidationError("sum of percents must be 100", status.HTTP_400_BAD_REQUEST)


def validate_payment_request_data(data: dict) -> None:
    """Run all validations for a payment/quote payload. Raises PaymentValidationError on error."""
    validate_currency(data)
    pm = data.get("payment_method")
    validate_payment_method(pm)
    installments = data.get("installments") or 1
    validate_installments(pm, installments)
    validate_splits(data.get("splits", []))