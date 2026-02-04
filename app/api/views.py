from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import PaymentRequestSerializer
from decimal import Decimal
from app.services.split_calculator import SimpleSplitCalculator, SplitCalculationError
from app.models import Payment, LedgerEntry, OutboxEvent
import uuid


class QuoteView(APIView):
    def post(self, request):
        serializer = PaymentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        amount = data["amount"]
        # validate basics
        if data["currency"] != "BRL":
            return Response({"detail": "unsupported currency"}, status=status.HTTP_400_BAD_REQUEST)

        calc = SimpleSplitCalculator()
        try:
            result = calc.calculate(amount=amount, payment_method=data["payment_method"], installments=data.get("installments") or 1, splits=data["splits"])
        except SplitCalculationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


class PaymentView(APIView):
    def post(self, request):
        serializer = PaymentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        idemp_key = request.headers.get("Idempotency-Key")

        # idempotency handling
        if idemp_key:
            existing = Payment.objects.filter(idempotency_key=idemp_key).first()
            if existing:
                # compare request bodies
                if existing.request_body == request.data:
                    # return previous result
                    ledger = list(existing.ledger_entries.values("recipient_id", "role", "amount"))
                    outbox = OutboxEvent.objects.filter(payload__payment_id=existing.payment_id).first()
                    resp = {
                        "payment_id": existing.payment_id,
                        "status": existing.status,
                        "gross_amount": f"{existing.gross_amount:.2f}",
                        "platform_fee_amount": f"{existing.platform_fee_amount:.2f}",
                        "net_amount": f"{existing.net_amount:.2f}",
                        "receivables": [{"recipient_id": l['recipient_id'], "role": l['role'], "amount": f"{l['amount']:.2f}"} for l in ledger],
                        "outbox_event": {"type": outbox.type, "status": outbox.status} if outbox else None,
                    }
                    return Response(resp)
                else:
                    return Response({"detail": "Idempotency key conflict: different payload"}, status=status.HTTP_409_CONFLICT)

        # validations
        if data["currency"] != "BRL":
            return Response({"detail": "unsupported currency"}, status=status.HTTP_400_BAD_REQUEST)

        if data["payment_method"].lower() == "pix" and data.get("installments"):
            return Response({"detail": "PIX does not accept installments"}, status=status.HTTP_400_BAD_REQUEST)

        splits = data["splits"]
        if not (1 <= len(splits) <= 5):
            return Response({"detail": "splits must be between 1 and 5"}, status=status.HTTP_400_BAD_REQUEST)
        total_pct = sum(s["percent"] for s in splits)
        if total_pct != 100:
            return Response({"detail": "sum of percents must be 100"}, status=status.HTTP_400_BAD_REQUEST)

        installments = data.get("installments") or 1
        if data["payment_method"].lower() == "card":
            if not (1 <= installments <= 12):
                return Response({"detail": "card installments must be between 1 and 12"}, status=status.HTTP_400_BAD_REQUEST)

        calc = SimpleSplitCalculator()
        try:
            result = calc.calculate(amount=data["amount"], payment_method=data["payment_method"], installments=installments, splits=splits)
        except SplitCalculationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # persist
        payment_id = f"pmt_{uuid.uuid4().hex[:8]}"
        payment = Payment.objects.create(
            payment_id=payment_id,
            status="captured",
            gross_amount=Decimal(result["gross_amount"]),
            platform_fee_amount=Decimal(result["platform_fee_amount"]),
            net_amount=Decimal(result["net_amount"]),
            payment_method=data["payment_method"],
            installments=installments,
            idempotency_key=idemp_key,
            request_body=request.data,
        )

        receivables = []
        for r in result["receivables"]:
            amount_r = Decimal(r["amount"])
            LedgerEntry.objects.create(payment=payment, recipient_id=r["recipient_id"], role=r.get("role"), amount=amount_r)
            receivables.append({"recipient_id": r["recipient_id"], "role": r.get("role"), "amount": r["amount"]})

        outbox = OutboxEvent.objects.create(type="payment_captured", payload={"payment_id": payment.payment_id, "status": "captured"}, status="pending")

        resp = {
            "payment_id": payment.payment_id,
            "status": payment.status,
            "gross_amount": result["gross_amount"],
            "platform_fee_amount": result["platform_fee_amount"],
            "net_amount": result["net_amount"],
            "receivables": receivables,
            "outbox_event": {"type": outbox.type, "status": outbox.status},
        }
        return Response(resp, status=status.HTTP_201_CREATED)
