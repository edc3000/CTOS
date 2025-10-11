from django.urls import path
from . import views

urlpatterns = [
    path("", views.metrics_home, name="metrics_home"),
    path("<str:indicator_id>/", views.indicator_detail, name="indicator_detail"),
    path("<str:indicator_id>/api/chart/", views.get_chart_image, name="get_chart_image"),
]