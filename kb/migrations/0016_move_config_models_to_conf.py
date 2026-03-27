from django.db import migrations, models


CONFIG_MODEL_NAMES = [
    "textextractionconfig",
    "secret",
    "chunkconfig",
    "llmconfig",
    "embeddingmodelconfig",
    "searchconfig",
    "knowledgegraphconfig",
]


def move_content_types_to_conf(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.filter(
        app_label="kb",
        model__in=CONFIG_MODEL_NAMES,
    ).update(app_label="conf")


class Migration(migrations.Migration):
    dependencies = [
        ("conf", "0001_initial"),
        ("kb", "0015_searchconfig"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name="chunk",
                    name="chunk_config",
                    field=models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="chunks",
                        to="conf.chunkconfig",
                    ),
                ),
                migrations.DeleteModel(name="ChunkConfig"),
                migrations.DeleteModel(name="EmbeddingModelConfig"),
                migrations.DeleteModel(name="KnowledgeGraphConfig"),
                migrations.DeleteModel(name="LLMConfig"),
                migrations.DeleteModel(name="SearchConfig"),
                migrations.DeleteModel(name="Secret"),
                migrations.DeleteModel(name="TextExtractionConfig"),
            ],
        ),
        migrations.RunPython(move_content_types_to_conf, migrations.RunPython.noop),
    ]
