from __future__ import annotations

from django.contrib import admin

from conf.models import (
    ChunkConfig,
    EmbeddingModelConfig,
    KnowledgeGraphConfig,
    LLMConfig,
    SearchConfig,
    Secret,
    TextExtractionConfig,
)


@admin.register(Secret)
class SecretAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("title", "date_created")
    search_fields = ("title",)


@admin.register(ChunkConfig)
class ChunkConfigAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("name", "date_created")


@admin.register(LLMConfig)
class LLMConfigAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("name", "provider", "model_name", "is_default", "date_created")
    list_filter = ("is_default",)


@admin.register(TextExtractionConfig)
class TextExtractionConfigAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("title", "date_created", "date_updated")
    search_fields = ("title",)


@admin.register(EmbeddingModelConfig)
class EmbeddingModelConfigAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("model_name", "model_provider", "is_active", "date_created")
    list_filter = ("is_active", "model_provider")
    search_fields = ("model_name", "model_provider")


@admin.register(SearchConfig)
class SearchConfigAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("name", "package_path", "date_created", "date_updated")
    search_fields = ("name", "package_path")


@admin.register(KnowledgeGraphConfig)
class KnowledgeGraphConfigAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("name", "package_name", "update_trigger", "is_active")
    list_filter = ("is_active", "update_trigger")
    search_fields = ("name", "package_name")
