from django.urls import path
from .views import QuoteView, PaymentView

urlpatterns = [
    path("checkout/quote", QuoteView.as_view(), name="quote"),
    path("payments", PaymentView.as_view(), name="payments"),
]
