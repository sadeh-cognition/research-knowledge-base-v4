from enum import Enum


class StreamUpdateType(str, Enum):
    STATUS = "status"
    RESULT = "result"


DEFAULT_JINA_CONFIG_TITLE = "JINA AI API"
DEFAULT_LLM_CONFIG_NAME = "Default Chat LLM"
DEFAULT_LLM_SECRET_TITLE = "DEFAULT_LLM_API_KEY"
DEFAULT_SEARCH_CONFIG_NAME = "semantic search"
DEFAULT_SEARCH_CONFIG_PACKAGE_PATH = "kb.services.search_engines.semantic_search.search"
