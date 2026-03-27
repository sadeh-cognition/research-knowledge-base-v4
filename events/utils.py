from django.db import transaction
from django.contrib.auth import get_user_model
from django_llm_chat.chat import Chat
from events.models import EventConsumer
from kb.services import llm as llm_service
from kb.services import chat as chat_service


User = get_user_model()
LLM_SERVICE_USERNAME = "litellm"
DEFAULT_CHAT_USERNAME = "djllmchat"
SYSTEM_USER_PASSWORD = "unused"


def create_chat_safely():
    """Create Chat instance safely, handling existing user conflicts."""
    try:
        with transaction.atomic():
            return Chat.create()
    except Exception as e:
        if "UNIQUE constraint failed" in str(e) or "UNIQUE constraint failed" in str(
            getattr(e, "__cause__", e)
        ):
            from django_llm_chat.models import Chat as ChatDBModel

            try:
                llm_user = User.objects.get(username=LLM_SERVICE_USERNAME)
            except User.DoesNotExist:
                llm_user, _ = User.objects.get_or_create(
                    username=LLM_SERVICE_USERNAME,
                    defaults={"password": SYSTEM_USER_PASSWORD},
                )

            default_user, _ = User.objects.get_or_create(
                username=DEFAULT_CHAT_USERNAME,
                defaults={"password": SYSTEM_USER_PASSWORD},
            )

            with transaction.atomic():
                db_model = ChatDBModel.objects.create()
                return Chat(
                    chat_db_model=db_model, llm_user=llm_user, default_user=default_user
                )
        raise


def get_or_create_consumer_user(username: str) -> "User":
    """Get or create the consumer user for automated LLM tasks."""
    user, _ = User.objects.get_or_create(
        username=username,
        defaults={"password": SYSTEM_USER_PASSWORD},
    )
    return user


def get_or_create_consumer(name: str) -> EventConsumer:
    consumer, _ = EventConsumer.objects.get_or_create(name=name)
    return consumer


def get_llm_config():
    default_config = chat_service.get_default_llm_config()

    if default_config:
        model_name = default_config.model_name
        provider = default_config.provider
        api_key = default_config.secret.value if default_config.secret else None
    else:
        raise ValueError("Default LLMConfig not found!")

    # We load credentials using the existing llm service setup if needed,
    # or rely on environment variables (like OPENROUTER_API_KEY)
    llm_service.setup_llm_config(model_name, provider, api_key)
    return model_name
