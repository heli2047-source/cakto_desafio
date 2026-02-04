from abc import ABC, abstractmethod
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal
from typing import Dict, List, Tuple

from .fee_strategy import get_fee_percentage


class SplitCalculatorInterface(ABC):
    @abstractmethod
    def calculate(self, *, amount: Decimal, payment_method: str, installments: int, splits: List[Dict]) -> Dict:
        pass


class SplitCalculationError(Exception):
    pass




class SimpleSplitCalculator(SplitCalculatorInterface):
    """Calculates platform fee, net amount and receivables following the rules.

    The calculator is open for extension: support for new payment methods
    is achieved by registering a `FeeStrategy` in `app.services.fee_strategy`.
    """

    def calculate(self, *, amount: Decimal, payment_method: str, installments: int, splits: List[Dict]) -> Dict:
        if amount <= 0:
            raise SplitCalculationError("amount must be > 0")

        try:
            pct = get_fee_percentage(payment_method, installments)
        except ValueError as e:
            raise SplitCalculationError(str(e))
        platform_fee = (pct / Decimal("100")) * amount
        platform_fee = platform_fee.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        net = (amount - platform_fee).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        # compute receivables
        receivables, total = self._compute_receivables(net, splits)

        # distribute remainder cents (if any)
        self._distribute_remainder(receivables, total, net, splits)

        # convert amounts to strings for JSON safety
        out_receivables = [
            {"recipient_id": r["recipient_id"], "role": r.get("role"), "amount": f"{r['amount']:.2f}"}
            for r in receivables
        ]

        return {
            "gross_amount": f"{amount.quantize(Decimal('0.01')):.2f}",
            "platform_fee_amount": f"{platform_fee:.2f}",
            "net_amount": f"{net:.2f}",
            "receivables": out_receivables,
        }

    def _compute_receivables(self, net: Decimal, splits: List[Dict]) -> Tuple[List[Dict], Decimal]:
        receivables: List[Dict] = []
        total = Decimal("0.00")
        for s in splits:
            share = (net * (Decimal(s["percent"]) / Decimal("100"))).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
            receivables.append({"recipient_id": s["recipient_id"], "role": s.get("role"), "amount": share})
            total += share
        return receivables, total

    def _distribute_remainder(self, receivables: List[Dict], total: Decimal, net: Decimal, splits: List[Dict]) -> None:
        diff = net - total
        if diff == Decimal("0.00"):
            return

        producer_idx = None
        max_pct = None
        max_idx = 0
        for idx, s in enumerate(splits):
            if s.get("role") == "producer":
                producer_idx = idx
                break
            if max_pct is None or s["percent"] > max_pct:
                max_pct = s["percent"]
                max_idx = idx

        target_idx = producer_idx if producer_idx is not None else max_idx
        receivables[target_idx]["amount"] = (receivables[target_idx]["amount"] + diff).quantize(Decimal("0.01"))
