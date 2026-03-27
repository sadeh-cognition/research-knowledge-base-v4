from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

from kb.api import api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
    path("chromadb/", include("django_chromadb_viz.urls")),
    path("llm-chat/", include("django_llm_chat.urls")),
    path("events/", include("events.urls")),
    path("sqlite-viz/", include("sqlite_viz.urls")),
    path(
        "ladybug-viz/",
        RedirectView.as_view(url="/ladybug-viz/ladybugdb/", permanent=False),
    ),
    path("ladybug-viz/", include("ladybug_viz.urls")),
]
