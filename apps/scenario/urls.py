from django.urls import path
from apps.scenario.views import (
    ParseQueryView, AirTablesView, AirDescriptionsView,
    SearchEventsView, AnalyzeView, PreviewSqlView,
)

urlpatterns = [
    path("parse/", ParseQueryView.as_view()),
    path("air-tables/", AirTablesView.as_view()),
    path("air-descriptions/", AirDescriptionsView.as_view()),
    path("search-events/", SearchEventsView.as_view()),
    path("analyze/", AnalyzeView.as_view()),
    path("preview-sql/", PreviewSqlView.as_view()),
]
