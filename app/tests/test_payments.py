from decimal import Decimal
from rest_framework.test import APITestCase


class PaymentsTests(APITestCase):
    base_url = "/api/v1/payments"

    def test_pix_100_split_100_producer(self):
        payload = {
            "amount": "100.00",
            "currency": "BRL",
            "payment_method": "pix",
            "splits": [{"recipient_id": "producer_1", "role": "producer", "percent": 100}],
        }
        r = self.client.post(self.base_url, payload, format="json", HTTP_IDEMPOTENCY_KEY="key-pix-100")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["platform_fee_amount"], "0.00")
        self.assertEqual(r.data["net_amount"], "100.00")
        self.assertEqual(r.data["receivables"][0]["amount"], "100.00")

    def test_card_3x_split_70_30(self):
        payload = {
            "amount": "297.00",
            "currency": "BRL",
            "payment_method": "card",
            "installments": 3,
            "splits": [
                {"recipient_id": "producer_1", "role": "producer", "percent": 70},
                {"recipient_id": "affiliate_9", "role": "affiliate", "percent": 30},
            ],
        }
        r = self.client.post(self.base_url, payload, format="json", HTTP_IDEMPOTENCY_KEY="key-card-3x")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["platform_fee_amount"], "26.70")
        self.assertEqual(r.data["net_amount"], "270.30")
        # receivables 70% and 30%
        amounts = [Decimal(x["amount"]) for x in r.data["receivables"]]
        self.assertEqual(sum(amounts), Decimal("270.30"))
        self.assertEqual(r.data["receivables"][0]["amount"], "189.21")
        self.assertEqual(r.data["receivables"][1]["amount"], "81.09")

    def test_rounding_diff_goes_to_producer(self):
        payload = {
            "amount": "100.01",
            "currency": "BRL",
            "payment_method": "pix",
            "splits": [
                {"recipient_id": "producer_1", "role": "producer", "percent": 50},
                {"recipient_id": "affiliate_1", "role": "affiliate", "percent": 50},
            ],
        }
        r = self.client.post(self.base_url, payload, format="json", HTTP_IDEMPOTENCY_KEY="key-rounding")
        self.assertEqual(r.status_code, 201)
        # net 100.01, split 50/50 -> halves 50.005 -> rounding makes 50.00 and 50.00, diff 0.01 goes to producer
        self.assertEqual(r.data["receivables"][0]["amount"], "50.01")
        self.assertEqual(r.data["receivables"][1]["amount"], "50.00")

    def test_idempotency_same_key_same_payload(self):
        payload = {
            "amount": "50.00",
            "currency": "BRL",
            "payment_method": "pix",
            "splits": [{"recipient_id": "producer_1", "role": "producer", "percent": 100}],
        }
        r1 = self.client.post(self.base_url, payload, format="json", HTTP_IDEMPOTENCY_KEY="key-1")
        self.assertEqual(r1.status_code, 201)
        pid = r1.data["payment_id"]

        r2 = self.client.post(self.base_url, payload, format="json", HTTP_IDEMPOTENCY_KEY="key-1")
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.data["payment_id"], pid)

    def test_idempotency_same_key_diff_payload_conflict(self):
        payload1 = {
            "amount": "60.00",
            "currency": "BRL",
            "payment_method": "pix",
            "splits": [{"recipient_id": "producer_1", "role": "producer", "percent": 100}],
        }
        payload2 = {
            "amount": "61.00",
            "currency": "BRL",
            "payment_method": "pix",
            "splits": [{"recipient_id": "producer_1", "role": "producer", "percent": 100}],
        }
        r1 = self.client.post(self.base_url, payload1, format="json", HTTP_IDEMPOTENCY_KEY="key-2")
        self.assertEqual(r1.status_code, 201)
        r2 = self.client.post(self.base_url, payload2, format="json", HTTP_IDEMPOTENCY_KEY="key-2")
        self.assertEqual(r2.status_code, 409)
