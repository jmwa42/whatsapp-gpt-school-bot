from django.contrib import admin
from .models import Transaction

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "phone",
        "amount",
        "status",
        "receipt_number",
        "transaction_date",
        "checkout_request_id",
    )
    list_filter = ("status", "transaction_date")
    search_fields = ("phone", "receipt_number", "checkout_request_id")

