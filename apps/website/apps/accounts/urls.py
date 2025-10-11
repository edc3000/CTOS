from django.urls import path
from . import views

urlpatterns = [
    path("", views.account_list, name="account_list"),
    path("api/balance/", views.get_account_balance, name="get_account_balance"),
    path("api/refresh/", views.refresh_all_accounts, name="refresh_all_accounts"),
    path("debug/", views.debug_data, name="debug_data"),
    path("<str:exchange>/<int:account_id>/", views.account_detail, name="account_detail"),
    path("<str:exchange>/<int:account_id>/api/positions/", views.get_account_positions, name="get_account_positions"),
    path("<str:exchange>/<int:account_id>/api/orders/", views.get_account_orders, name="get_account_orders"),
]