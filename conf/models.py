from django.db import models

from kb.services.llm import LLMProvider


class EmbeddingProvider(models.TextChoices):
    LMSTUDIO = "LMStudio", "LMStudio"


class KnowledgeGraphUpdateTrigger(models.TextChoices):
    ALWAYS = "always", "Each time I send a message"
    LLM_INTENT = "llm_intent", "When I ask for an update explicitly"


DEFAULT_KNOWLEDGE_GRAPH_PACKAGE_NAME = "django_lightrag"


class TextExtractionConfig(models.Model):
    title: models.CharField = models.CharField(max_length=255, unique=True)
    details: models.JSONField = models.JSONField(default=dict)
    date_created: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    date_updated: models.DateTimeField = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]
        db_table = "kb_textextractionconfig"

    def __str__(self) -> str:
        return self.title


class Secret(models.Model):
    title: models.CharField = models.CharField(max_length=255, unique=True)
    value: models.TextField = models.TextField()
    text_extraction_config: models.ForeignKey = models.ForeignKey(
        TextExtractionConfig,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="secrets",
    )
    date_created: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    date_updated: models.DateTimeField = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]
        db_table = "kb_secret"

    def __str__(self) -> str:
        return self.title


class ChunkConfig(models.Model):
    name: models.CharField = models.CharField(max_length=255, unique=True)
    details: models.JSONField = models.JSONField(default=dict)
    date_created: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    date_updated: models.DateTimeField = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        db_table = "kb_chunkconfig"

    def __str__(self) -> str:
        return self.name


class LLMConfig(models.Model):
    name: models.CharField = models.CharField(max_length=255, unique=True)
    model_name: models.CharField = models.CharField(max_length=255)
    provider: models.CharField = models.CharField(
        max_length=255,
        choices=[(tag.value, tag.name) for tag in LLMProvider],
        default=LLMProvider.OPENAI.value,
    )
    is_default: models.BooleanField = models.BooleanField(default=False)
    secret: models.ForeignKey = models.ForeignKey(
        Secret,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="llm_configs",
    )
    date_created: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    date_updated: models.DateTimeField = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        db_table = "kb_llmconfig"

    def __str__(self) -> str:
        return f"{self.name} ({self.model_name})"


class EmbeddingModelConfig(models.Model):
    model_name: models.CharField = models.CharField(max_length=255)
    model_provider: models.CharField = models.CharField(max_length=255)
    is_active: models.BooleanField = models.BooleanField(default=False)
    date_created: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    date_updated: models.DateTimeField = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_active", "date_created"]
        db_table = "kb_embeddingmodelconfig"

    def __str__(self) -> str:
        return f"{self.model_name} ({self.model_provider})"


class SearchConfig(models.Model):
    name: models.CharField = models.CharField(max_length=255, unique=True)
    package_path: models.CharField = models.CharField(max_length=255)
    date_created: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    date_updated: models.DateTimeField = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        db_table = "kb_searchconfig"

    def __str__(self) -> str:
        return f"{self.name} ({self.package_path})"


class KnowledgeGraphConfig(models.Model):
    name: models.CharField = models.CharField(max_length=255, unique=True)
    package_name: models.CharField = models.CharField(
        max_length=255, default=DEFAULT_KNOWLEDGE_GRAPH_PACKAGE_NAME
    )
    update_trigger: models.CharField = models.CharField(
        max_length=255,
        choices=KnowledgeGraphUpdateTrigger.choices,
        default=KnowledgeGraphUpdateTrigger.ALWAYS,
    )
    is_active: models.BooleanField = models.BooleanField(default=False)
    date_created: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    date_updated: models.DateTimeField = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        db_table = "kb_knowledgegraphconfig"

    def __str__(self) -> str:
        return f"{self.name} ({self.package_name})"
