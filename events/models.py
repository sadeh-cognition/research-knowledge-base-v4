from django.db import models

class EntityTypes(models.TextChoices):
    RESOURCE = "resource", "Resource"

class EventDescriptions(models.TextChoices):
    TEXT_EXTRACTED = "text extracted from resource", "Text Extracted From Resource"
    CLEAN_UP_FINISHED = "extracted text clean up finished", "Extracted Text Clean Up Finished"

class Event(models.Model):
    entity = models.CharField(max_length=50, choices=EntityTypes.choices)
    entity_id = models.CharField(max_length=255)
    description = models.CharField(max_length=255, choices=EventDescriptions.choices)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_created"]

    def __str__(self) -> str:
        return f"{self.get_entity_display()} {self.entity_id}: {self.get_description_display()}"


class EventConsumer(models.Model):
    name = models.CharField(max_length=255, unique=True)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class EventConsumed(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    consumer = models.ForeignKey(EventConsumer, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("event", "consumer")]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Event {self.event_id} consumed by {self.consumer.name}"
