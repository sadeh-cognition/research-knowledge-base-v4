import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("kb", "0015_searchconfig"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="TextExtractionConfig",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        ("title", models.CharField(max_length=255, unique=True)),
                        ("details", models.JSONField(default=dict)),
                        ("date_created", models.DateTimeField(auto_now_add=True)),
                        ("date_updated", models.DateTimeField(auto_now=True)),
                    ],
                    options={
                        "ordering": ["title"],
                        "db_table": "kb_textextractionconfig",
                    },
                ),
                migrations.CreateModel(
                    name="Secret",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        ("title", models.CharField(max_length=255, unique=True)),
                        ("value", models.TextField()),
                        ("date_created", models.DateTimeField(auto_now_add=True)),
                        ("date_updated", models.DateTimeField(auto_now=True)),
                        (
                            "text_extraction_config",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.SET_NULL,
                                related_name="secrets",
                                to="conf.textextractionconfig",
                            ),
                        ),
                    ],
                    options={
                        "ordering": ["title"],
                        "db_table": "kb_secret",
                    },
                ),
                migrations.CreateModel(
                    name="ChunkConfig",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        ("name", models.CharField(max_length=255, unique=True)),
                        ("details", models.JSONField(default=dict)),
                        ("date_created", models.DateTimeField(auto_now_add=True)),
                        ("date_updated", models.DateTimeField(auto_now=True)),
                    ],
                    options={
                        "ordering": ["name"],
                        "db_table": "kb_chunkconfig",
                    },
                ),
                migrations.CreateModel(
                    name="EmbeddingModelConfig",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        ("model_name", models.CharField(max_length=255)),
                        ("model_provider", models.CharField(max_length=255)),
                        ("is_active", models.BooleanField(default=False)),
                        ("date_created", models.DateTimeField(auto_now_add=True)),
                        ("date_updated", models.DateTimeField(auto_now=True)),
                    ],
                    options={
                        "ordering": ["-is_active", "date_created"],
                        "db_table": "kb_embeddingmodelconfig",
                    },
                ),
                migrations.CreateModel(
                    name="SearchConfig",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        ("name", models.CharField(max_length=255, unique=True)),
                        ("package_path", models.CharField(max_length=255)),
                        ("date_created", models.DateTimeField(auto_now_add=True)),
                        ("date_updated", models.DateTimeField(auto_now=True)),
                    ],
                    options={
                        "ordering": ["name"],
                        "db_table": "kb_searchconfig",
                    },
                ),
                migrations.CreateModel(
                    name="KnowledgeGraphConfig",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        ("name", models.CharField(max_length=255, unique=True)),
                        (
                            "package_name",
                            models.CharField(default="django_lightrag", max_length=255),
                        ),
                        (
                            "update_trigger",
                            models.CharField(
                                choices=[
                                    ("always", "Each time I send a message"),
                                    (
                                        "llm_intent",
                                        "When I ask for an update explicitly",
                                    ),
                                ],
                                default="always",
                                max_length=255,
                            ),
                        ),
                        ("is_active", models.BooleanField(default=False)),
                        ("date_created", models.DateTimeField(auto_now_add=True)),
                        ("date_updated", models.DateTimeField(auto_now=True)),
                    ],
                    options={
                        "ordering": ["name"],
                        "db_table": "kb_knowledgegraphconfig",
                    },
                ),
                migrations.CreateModel(
                    name="LLMConfig",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        ("name", models.CharField(max_length=255, unique=True)),
                        ("model_name", models.CharField(max_length=255)),
                        (
                            "provider",
                            models.CharField(
                                choices=[
                                    ("openrouter", "OPENROUTER"),
                                    ("groq", "GROQ"),
                                    ("openai", "OPENAI"),
                                    ("anthropic", "ANTHROPIC"),
                                    ("lmstudio", "LMSTUDIO"),
                                ],
                                default="openai",
                                max_length=255,
                            ),
                        ),
                        ("is_default", models.BooleanField(default=False)),
                        ("date_created", models.DateTimeField(auto_now_add=True)),
                        ("date_updated", models.DateTimeField(auto_now=True)),
                        (
                            "secret",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.SET_NULL,
                                related_name="llm_configs",
                                to="conf.secret",
                            ),
                        ),
                    ],
                    options={
                        "ordering": ["name"],
                        "db_table": "kb_llmconfig",
                    },
                ),
            ],
        ),
    ]
