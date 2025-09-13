# mpesa/models.py
from django.db import models

class Transaction(models.Model):
    STATUS_CHOICES = [
        ("initiated", "Initiated"),
        ("success", "Success"),
        ("failed", "Failed"),
    ]

    phone = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="initiated")

    # STK push request/response
    merchant_request_id = models.CharField(max_length=100, null=True, blank=True)
    checkout_request_id = models.CharField(max_length=100, null=True, blank=True)
    raw_response = models.JSONField(null=True, blank=True)   # initial STK push response

    # Callback data
    result_code = models.IntegerField(null=True, blank=True)
    result_desc = models.TextField(null=True, blank=True)
    receipt_number = models.CharField(max_length=50, null=True, blank=True)
    transaction_date = models.BigIntegerField(null=True, blank=True)  # YYYYMMDDHHMMSS
    raw_callback = models.JSONField(null=True, blank=True)            # full callback JSON

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.phone} - {self.amount} [{self.status}]"

