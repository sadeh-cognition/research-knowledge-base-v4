import pytest
from conf.models import EmbeddingProvider
from kb.models import EmbeddingModelConfig
from kb.services.chromadb_service import _get_embeddings


@pytest.mark.django_db
def test_embedding_config_exists():
    """Verify that the default embedding config was seeded."""
    config = EmbeddingModelConfig.objects.filter(is_active=True).first()
    assert config is not None
    assert config.model_name == "text-embedding-embeddinggemma-300m"
    assert config.model_provider == EmbeddingProvider.LMSTUDIO
    assert config.is_active is True


@pytest.mark.django_db
def test_get_embeddings_integration(mocker):
    """Verify that _get_embeddings calls generate_embeddings from embed_gen."""
    mock_gen = mocker.patch(
        "kb.services.chromadb_service.generate_embeddings", return_value=[[0.1, 0.2]]
    )

    embeddings = _get_embeddings(["test"])

    assert embeddings == [[0.1, 0.2]]
    mock_gen.assert_called_once()
    args, kwargs = mock_gen.call_args
    assert kwargs["texts"] == ["test"]
    assert "model_name" in kwargs
    assert "provider" in kwargs
    assert "base_url" in kwargs
