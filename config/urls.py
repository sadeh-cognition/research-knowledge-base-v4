from django.contrib import admin
from django.urls import path, include

from kb.api import api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
    path("chromadb/", include("django_chromadb_viz.urls")),
    path("llm-chat/", include("django_llm_chat.urls")),
    path("events/", include("events.urls")),
]
