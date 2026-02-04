from abc import ABC, abstractmethod
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from typing import List, Dict, Tuple


class SplitCalculatorInterface(ABC):
    @abstractmethod
    def calculate(self, *, amount: Decimal, payment_method: str, installments: int, splits: List[Dict]) -> Dict:
        pass


class SplitCalculationError(Exception):
    pass


class SimpleSplitCalculator(SplitCalculatorInterface):
    """Calculates platform fee, net amount and receivables following the rules:
    - PIX: 0%
    - CARD 1x: 3.99%
    - CARD 2x-12x: 4.99% + 2% * (installments - 1)
    Rounding: uses Decimal with 2 places; any cent rounding difference goes to role='producer' or highest percent.
    """

    def _platform_fee_pct(self, payment_method: str, installments: int) -> Decimal:
        if payment_method.lower() == "pix":
            return Decimal("0.00")
        if installments == 1:
            return Decimal("3.99")
        return Decimal("4.99") + Decimal("2.00") * Decimal(installments - 1)

    def calculate(self, *, amount: Decimal, payment_method: str, installments: int, splits: List[Dict]) -> Dict:
        if amount <= 0:
            raise SplitCalculationError("amount must be > 0")

        pct = self._platform_fee_pct(payment_method, installments)
        platform_fee = (pct / Decimal("100")) * amount
        platform_fee = platform_fee.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        net = (amount - platform_fee).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # compute receivables
        receivables: List[Dict] = []
        total = Decimal("0.00")
        for s in splits:
            share = (net * (Decimal(s["percent"]) / Decimal("100"))).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
            receivables.append({"recipient_id": s["recipient_id"], "role": s.get("role"), "amount": share})
            total += share

        # distribute remainder cents
        diff = net - total
        if diff != Decimal("0.00"):
            # find producer
            producer_idx = None
            max_pct = None
            for idx, s in enumerate(splits):
                if s.get("role") == "producer":
                    producer_idx = idx
                    break
                if max_pct is None or s["percent"] > max_pct:
                    max_pct = s["percent"]
                    max_idx = idx
            target_idx = producer_idx if producer_idx is not None else max_idx
            receivables[target_idx]["amount"] = (receivables[target_idx]["amount"] + diff).quantize(Decimal("0.01"))

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
