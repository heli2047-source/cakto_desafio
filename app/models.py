from django.db import models
from django.utils import timezone


class Payment(models.Model):
    payment_id = models.CharField(max_length=64, unique=True)
    status = models.CharField(max_length=32)
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2)
    platform_fee_amount = models.DecimalField(max_digits=12, decimal_places=2)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=32)
    installments = models.IntegerField(null=True, blank=True)
    idempotency_key = models.CharField(max_length=128, null=True, blank=True, db_index=True)
    request_body = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.payment_id


class LedgerEntry(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="ledger_entries")
    recipient_id = models.CharField(max_length=64)
    role = models.CharField(max_length=32)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.recipient_id}:{self.amount}"


class OutboxEvent(models.Model):
    type = models.CharField(max_length=64)
    payload = models.JSONField()
    status = models.CharField(max_length=32, default="pending")
    created_at = models.DateTimeField(default=timezone.now)
    published_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.type}:{self.status}"
