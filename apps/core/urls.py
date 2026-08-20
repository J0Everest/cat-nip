from django.urls import path
from apps.core.views import ConfigView, NextQuarterView, HealthView

urlpatterns = [
    path("config/", ConfigView.as_view()),
    path("config/next-quarter/", NextQuarterView.as_view()),
    path("health/", HealthView.as_view()),
]
