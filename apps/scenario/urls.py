from django.urls import path
from apps.scenario.views import (
    ParseQueryView, AirTablesView, AirDescriptionsView,
    SearchEventsView, AnalyzeView, PreviewSqlView,
    SavedScenarioListCreateView, SavedScenarioDetailView,
    ModelInfoView, ZonesView,
)

urlpatterns = [
    path("parse/", ParseQueryView.as_view()),
    path("zones/", ZonesView.as_view()),
    path("air-tables/", AirTablesView.as_view()),
    path("air-descriptions/", AirDescriptionsView.as_view()),
    path("search-events/", SearchEventsView.as_view()),
    path("analyze/", AnalyzeView.as_view()),
    path("preview-sql/", PreviewSqlView.as_view()),
    path("saved/", SavedScenarioListCreateView.as_view()),
    path("saved/<int:pk>/", SavedScenarioDetailView.as_view()),
    path("model-info/", ModelInfoView.as_view()),
]
