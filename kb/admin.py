from __future__ import annotations

from django.contrib import admin

from kb.models import Chunk, Resource


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("id", "url", "resource_type", "date_created")
    list_filter = ("resource_type",)
    search_fields = ("url",)


@admin.register(Chunk)
class ChunkAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("text", "resource", "order", "date_created")
    list_filter = ("resource",)
