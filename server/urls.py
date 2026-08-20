from django.urls import path, include, re_path
from django.http import HttpResponse
from pathlib import Path
from django.conf import settings


def _angular_index(request):
    index = Path(settings.BASE_DIR) / "static" / "angular" / "browser" / "index.html"
    if index.exists():
        return HttpResponse(index.read_text(), content_type="text/html")
    return HttpResponse("<h1>Angular build not found. Run build.sh first.</h1>", status=404)


urlpatterns = [
    path("api/v1/", include("apps.core.urls")),
    path("api/v1/scenario/", include("apps.scenario.urls")),
    re_path(r"^(?!api/|static/).*$", _angular_index),
]
