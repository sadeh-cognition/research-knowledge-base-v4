from django.contrib import admin
from .models import Event, EventConsumer, EventConsumed


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("id", "entity", "entity_id", "description", "date_created")
    list_filter = ("entity", "description", "date_created")
    search_fields = ("entity_id", "description")


@admin.register(EventConsumer)
class EventConsumerAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "date_created")
    search_fields = ("name",)


@admin.register(EventConsumed)
class EventConsumedAdmin(admin.ModelAdmin):
    list_display = ("id", "event", "consumer", "status", "created_at")
    list_filter = ("consumer", "created_at")
