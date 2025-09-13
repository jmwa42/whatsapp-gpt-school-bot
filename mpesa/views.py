# mpesa/views.py
import json
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import Transaction
from decimal import Decimal, InvalidOperation
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import uuid


@csrf_exempt
def stk_push(request):
    """
    Initiates an STK Push request and saves the transaction.
    """
    if request.method == "POST":
        data = json.loads(request.body)
        phone_number = data.get("phone_number")
        amount = data.get("amount")

        # ✅ Replace with your Safaricom API call (dummy response here for structure)
        # response = requests.post(MPESA_URL, headers=HEADERS, json=payload).json()

        response = {
            "MerchantRequestID": "12345-67890",
            "CheckoutRequestID": "ws_CO_210820252310363713541274",
            "ResponseCode": "0",
            "CustomerMessage": "Success. Request accepted for processing",
        }

        # ✅ Save transaction in DB
        Transaction.objects.create(
            phone_number=phone_number,
            amount=amount,
            checkout_request_id=response.get("CheckoutRequestID"),
            merchant_request_id=response.get("MerchantRequestID"),
            status="Pending",
            raw_response=response,
            created_at=timezone.now(),
        )

        return JsonResponse(response)

    return JsonResponse({"error": "Invalid method"}, status=400)

def _to_decimal(val):
    if val is None:
        return None
    try:
        return Decimal(str(val))
    except (InvalidOperation, TypeError, ValueError):
        return None


@csrf_exempt
def register_init(request):
    print("🔥 register_init view hit!")
    import traceback, sys

    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    try:
        body = request.body.decode("utf-8")
        print("📥 Raw body:", body)  # log raw body
        payload = json.loads(body or "{}")
    except Exception as e:
        print("❌ JSON parse error:", e)
        payload = request.POST.dict()

    try:
        merchant_request_id = payload.get("MerchantRequestID")
        checkout_request_id = payload.get("CheckoutRequestID")
        phone = str(payload.get("PhoneNumber") or "")
        amount = payload.get("Amount") or 0

        print("✅ Parsed payload:", payload)

        tx, created = Transaction.objects.update_or_create(
            checkout_request_id=checkout_request_id,
            defaults={
                "merchant_request_id": merchant_request_id,
                "phone": phone,
                "amount": amount,
                "status": "initiated",
            },
        )
        return JsonResponse({"ok": True, "created": created, "id": tx.id})
    except Exception as e:
        print("❌ Exception in register_init:", e)
        traceback.print_exc(file=sys.stdout)
        return JsonResponse({"ok": False, "error": str(e)}, status=500)
 
 
 
@csrf_exempt
@require_POST
def mpesa_callback(request):
    # 1) Parse JSON safely
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ResultCode": 1, "ResultDesc": "Invalid JSON"})

    print("🔔 M-Pesa Callback Body:", payload)

    # 2) Extract top-level fields
    stk = payload.get("Body", {}).get("stkCallback", {})
    checkout_id = stk.get("CheckoutRequestID")
    merchant_id = stk.get("MerchantRequestID")  # present in prod/sandbox callbacks
    result_code = stk.get("ResultCode")
    result_desc = stk.get("ResultDesc")

    # 3) Normalize metadata into a dict
    items = {}
    for item in stk.get("CallbackMetadata", {}).get("Item", []):
        name = item.get("Name")
        value = item.get("Value")
        if name:
            items[name] = value

    amount = _to_decimal(items.get("Amount"))
    receipt = items.get("MpesaReceiptNumber")
    phone = str(items.get("PhoneNumber")) if items.get("PhoneNumber") is not None else None
    trans_date = str(items.get("TransactionDate")) if items.get("TransactionDate") is not None else None

    if not checkout_id:
        # Without a CheckoutRequestID we can’t key this transaction reliably
        return JsonResponse({"ResultCode": 1, "ResultDesc": "Missing CheckoutRequestID"})

    # 4) UPSERT by CheckoutRequestID (create if missing, update if present)
    #    This makes the system resilient even if the STK push was not recorded by Django.
    tx, created = Transaction.objects.get_or_create(
        checkout_request_id=checkout_id,
        defaults={
            "merchant_request_id": merchant_id,
            "phone": phone or "",
            "amount": amount or Decimal("0"),
            "status": "initiated",
            "raw_response": None,     # reserved for STK init responses
        },
    )

    # 5) Update with callback data
    tx.result_code = result_code
    tx.result_desc = result_desc
    tx.receipt_number = receipt
    if phone:
        tx.phone = phone
    if amount is not None:
        tx.amount = amount
    tx.transaction_date = trans_date
    tx.status = "success" if str(result_code) == "0" else "failed"
    tx.raw_callback = payload
    tx.save()

    print(("🆕 Created via callback:" if created else "✅ Updated existing:"),
          {"id": tx.id, "checkout_request_id": tx.checkout_request_id, "status": tx.status})

    # 6) Always ACK to Safaricom
    return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})

    
    
# ------------------------------
# DEBUG VIEW
# ------------------------------
def debug_transactions(request):
    if not settings.DEBUG:
        return JsonResponse({"error": "not allowed"}, status=403)
    rows = list(Transaction.objects.order_by("-created_at").values())
    return JsonResponse({"count": len(rows), "rows": rows})
