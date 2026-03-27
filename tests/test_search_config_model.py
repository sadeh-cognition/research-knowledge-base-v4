import pytest
from django.db import IntegrityError
from model_bakery import baker

from kb.constants import DEFAULT_SEARCH_CONFIG_NAME, DEFAULT_SEARCH_CONFIG_PACKAGE_PATH
from kb.models import SearchConfig


def test_seeded_default_search_config_exists(db):
    config = SearchConfig.objects.get(name=DEFAULT_SEARCH_CONFIG_NAME)

    assert config.package_path == DEFAULT_SEARCH_CONFIG_PACKAGE_PATH


def test_search_config_name_uniqueness_is_enforced(db):
    baker.make(
        SearchConfig,
        name="duplicate",
        package_path="tests.search_engines.valid_engine",
    )

    with pytest.raises(IntegrityError):
        baker.make(
            SearchConfig,
            name="duplicate",
            package_path="tests.search_engines.explicit_engine",
        )
