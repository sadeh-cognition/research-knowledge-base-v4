from django.db import models


class ResourceType(models.TextChoices):
    PAPER = "paper", "Paper"
    BLOG_POST = "blog_post", "Blog Post"


class Resource(models.Model):
    url: models.URLField = models.URLField(unique=True)
    resource_type: models.CharField = models.CharField(
        max_length=20, choices=ResourceType.choices
    )
    title: models.CharField = models.CharField(max_length=255, blank=True, default="")
    extracted_text: models.TextField = models.TextField(blank=True, default="")
    summary: models.TextField = models.TextField(blank=True, default="")
    date_created: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    date_updated: models.DateTimeField = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date_created"]

    def __str__(self) -> str:
        return f"{self.get_resource_type_display()}: {self.url}"


class Chunk(models.Model):
    text: models.TextField = models.TextField()
    order: models.PositiveIntegerField = models.PositiveIntegerField()
    resource: models.ForeignKey = models.ForeignKey(
        Resource, on_delete=models.CASCADE, related_name="chunks"
    )
    chunk_config: models.ForeignKey = models.ForeignKey(
        "conf.ChunkConfig", on_delete=models.CASCADE, related_name="chunks"
    )
    date_created: models.DateTimeField = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["resource", "order"]
        unique_together = [("resource", "order")]

    def __str__(self) -> str:
        return f"Chunk {self.order} of Resource {self.resource_id}"


class ResourceChat(models.Model):
    resource: models.ForeignKey = models.ForeignKey(
        Resource, on_delete=models.CASCADE, related_name="resource_chats"
    )
    chat_id: models.IntegerField = models.IntegerField(unique=True)
    date_created: models.DateTimeField = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_created"]

    def __str__(self) -> str:
        return f"Chat {self.chat_id} for Resource {self.resource_id}"


class Reference(models.Model):
    resource = models.ForeignKey(
        Resource, on_delete=models.CASCADE, related_name="references"
    )
    description = models.TextField()
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_created"]

    def __str__(self) -> str:
        return f"Reference for Resource {self.resource_id}"


from conf.models import (
    ChunkConfig,
    EmbeddingModelConfig,
    KnowledgeGraphConfig,
    LLMConfig,
    SearchConfig,
    Secret,
    TextExtractionConfig,
)
