from rest_framework import serializers


class SplitSerializer(serializers.Serializer):
    recipient_id = serializers.CharField()
    role = serializers.CharField()
    percent = serializers.IntegerField()


class PaymentRequestSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField()
    payment_method = serializers.CharField()
    installments = serializers.IntegerField(required=False, allow_null=True)
    splits = SplitSerializer(many=True)
