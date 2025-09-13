from django.urls import path
from . import views   # ✅ import views from current app

urlpatterns = [
    path("stkpush/", views.stk_push, name="stkpush"),
    path("callback/", views.mpesa_callback, name="callback"),
   #S path("debug/", views.debug_transactions, name="debug_tx"),
    path("register-init/", views.register_init, name="register_init"),
]

