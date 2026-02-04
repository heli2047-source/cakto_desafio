from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict


class FeeStrategy(ABC):
    """Pluggable strategy for computing platform fee percentage.

    Implementations should return a Decimal percentage (e.g. 3.99).
    """

    @abstractmethod
    def percentage(self, installments: int) -> Decimal:
        pass


_fee_registry: Dict[str, FeeStrategy] = {}


def register_fee_strategy(name: str):
    def _decorator(cls):
        _fee_registry[name.lower()] = cls()
        return cls

    return _decorator


@register_fee_strategy("pix")
class PixFeeStrategy(FeeStrategy):
    def percentage(self, installments: int) -> Decimal:
        return Decimal("0.00")


@register_fee_strategy("card")
class CardFeeStrategy(FeeStrategy):
    def percentage(self, installments: int) -> Decimal:
        if installments == 1:
            return Decimal("3.99")
        return Decimal("4.99") + Decimal("2.00") * Decimal(installments - 1)


def get_fee_percentage(payment_method: str, installments: int) -> Decimal:
    strategy = _fee_registry.get(payment_method.lower())
    if not strategy:
        raise ValueError(f"unsupported payment_method: {payment_method}")
    return strategy.percentage(installments)


def supported_payment_methods():
    """Return a list of registered payment method names (lowercased)."""
    return list(_fee_registry.keys())
