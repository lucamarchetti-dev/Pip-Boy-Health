from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("collect/", views.collect_now, name="collect_now"),
    path("api/metrics/", views.api_metrics, name="api_metrics"),
]
