import importlib
import os
import traceback
from collections.abc import Callable

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from loguru import logger

from conf.models import ChunkConfig, KnowledgeGraphConfig, KnowledgeGraphUpdateTrigger
from events.models import (
    ConsumptionStatus,
    EntityTypes,
    Event,
    EventConsumed,
    EventConsumer,
    EventDescriptions,
)
from events.services import fire_event
from events.utils import (
    create_chat_safely,
    get_llm_config,
    get_or_create_consumer,
    get_or_create_consumer_user,
)
from .check_kg_update import consume_check_kg_update
from .chunk_and_embed import consume_chunk_and_embed
from .clean_up_extracted_text import consume_clean_up_extracted_text
from .extract_references import consume_extract_references
from .extract_title_of_resource import consume_extract_title_of_resource
from .summarize import consume_summarize
from .update_knowledge_graph import consume_update_knowledge_graph

__all__ = [
    "ChunkConfig",
    "KnowledgeGraphConfig",
    "KnowledgeGraphUpdateTrigger",
    "consume_check_kg_update",
    "consume_chunk_and_embed",
    "consume_clean_up_extracted_text",
    "consume_extract_references",
    "consume_extract_title_of_resource",
    "consume_summarize",
    "consume_update_knowledge_graph",
    "fire_event",
    "get_object_or_404",
    "importlib",
    "process_all_events",
]

User = get_user_model()


def _is_pytest_mode() -> bool:
    return bool(os.environ.get("PYTEST_CURRENT_TEST"))


def _get_next_unprocessed_event(
    consumer: EventConsumer,
    *,
    entity: EntityTypes,
    description: EventDescriptions,
) -> Event | None:
    events = Event.objects.filter(entity=entity, description=description).order_by("id")

    if settings.EVENT_CONSUMER_RETRY_FAILED:
        events = events.exclude(
            eventconsumed__consumer=consumer,
            eventconsumed__status=ConsumptionStatus.OK,
        )
    else:
        events = events.exclude(eventconsumed__consumer=consumer)

    return events.first()


def _mark_event_consumed(
    *,
    event: Event,
    consumer: EventConsumer,
    status: ConsumptionStatus,
    exception: str | None = None,
) -> None:
    EventConsumed.objects.update_or_create(
        event=event,
        consumer=consumer,
        defaults={"status": status, "exception": exception},
    )


def _call_llm(
    *,
    username: str,
    system_prompt: str,
    message: str,
    fallback: str,
    error_log_message: str,
) -> str:
    if _is_pytest_mode():
        return fallback

    try:
        chat_instance = create_chat_safely()
        user = get_or_create_consumer_user(username)
        chat_instance.create_system_message(system_prompt, user)
        chat_instance.call_llm(
            model_name=get_llm_config(),
            message=message,
            user=user,
        )
        return chat_instance.last_llm_message.text or ""
    except Exception as exc:
        logger.error(f"{error_log_message}: {exc}")
        return fallback


def _run_consumer(
    *,
    consumer_name: str,
    entity: EntityTypes,
    description: EventDescriptions,
    handler: Callable[[Event], str | None],
) -> int:
    logger.info(f"Running consumer: {consumer_name}")
    consumer = get_or_create_consumer(consumer_name)
    event = _get_next_unprocessed_event(
        consumer,
        entity=entity,
        description=description,
    )

    if event is None:
        logger.info(f"Finished consumer '{consumer_name}', processed 0 events")
        return 0

    logger.info(
        f"Consumer '{consumer_name}' found event {event.id}. Starting processing..."
    )

    try:
        with transaction.atomic():
            success_message = handler(event)
            _mark_event_consumed(
                event=event,
                consumer=consumer,
                status=ConsumptionStatus.OK,
            )

        if success_message:
            logger.info(success_message)

        logger.info(f"Finished consumer '{consumer_name}', processed 1 events")
        return 1
    except Exception:
        stacktrace = traceback.format_exc()
        logger.exception(f"Failed to process {consumer_name} for event {event.id}")
        with transaction.atomic():
            _mark_event_consumed(
                event=event,
                consumer=consumer,
                status=ConsumptionStatus.ERROR,
                exception=stacktrace,
            )

        logger.info(f"Finished consumer '{consumer_name}', processed 0 events")
        return 0


def process_all_events() -> int:
    """Process one event per consumer and return the total processed count."""

    count = 0
    count += consume_clean_up_extracted_text()
    count += consume_summarize()
    count += consume_chunk_and_embed()
    count += consume_extract_title_of_resource()
    count += consume_extract_references()
    count += consume_check_kg_update()
    count += consume_update_knowledge_graph()
    return count
