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
from kb.models import Reference, Resource

from .utils import (
    create_chat_safely,
    get_llm_config,
    get_or_create_consumer,
    get_or_create_consumer_user,
)

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


def consume_clean_up_extracted_text() -> int:
    """Clean up extracted resource text."""

    system_prompt = (
        "You are an assistant that cleans up extracted text from resources. "
        "Your task is to remove all non-human-readable text, random numbers, "
        "useless strings of letters, and excessive whitespace. "
        "You must keep all human-readable text 100% intact. "
        "Return ONLY the cleaned text and nothing else."
    )

    def handler(event: Event) -> str:
        resource = get_object_or_404(Resource, id=event.entity_id)
        logger.info(
            f"Calling LLM to clean up extracted text for Resource {resource.id}..."
        )

        cleaned_text = (
            f"MOCKED CLEANED TEXT: {resource.extracted_text}"
            if _is_pytest_mode()
            else _call_llm(
                username="rkb-consumer-cleanup",
                system_prompt=system_prompt,
                message=resource.extracted_text,
                fallback=resource.extracted_text,
                error_log_message="Error calling LLM for clean up",
            )
        )

        resource.extracted_text = cleaned_text
        resource.save()

        logger.info(f"Firing 'clean up finished' event for Resource {resource.id}...")
        fire_event(
            entity=EntityTypes.RESOURCE,
            entity_id=event.entity_id,
            description=EventDescriptions.CLEAN_UP_FINISHED,
            triggered_by="Clean up extracted text",
        )

        return f"Consumed 'text extracted' event {event.id} for Resource {resource.id}"

    return _run_consumer(
        consumer_name="Clean up extracted text",
        entity=EntityTypes.RESOURCE,
        description=EventDescriptions.TEXT_EXTRACTED,
        handler=handler,
    )


def consume_summarize() -> int:
    """Summarize cleaned resource text."""

    system_prompt = (
        "You are an assistant that summarizes text. "
        "Please provide a concise and informative summary of the following text."
    )

    def handler(event: Event) -> str:
        resource = get_object_or_404(Resource, id=event.entity_id)
        logger.info(f"Calling LLM to summarize text for Resource {resource.id}...")

        summary_text = (
            f"MOCKED SUMMARY: {resource.extracted_text}"
            if _is_pytest_mode()
            else _call_llm(
                username="rkb-consumer-summarize",
                system_prompt=system_prompt,
                message=resource.extracted_text,
                fallback="Error generating summary.",
                error_log_message="Error calling LLM for summarize",
            )
        )

        resource.summary = summary_text
        resource.save()
        return (
            f"Consumed 'clean up finished' event {event.id} for Resource {resource.id}"
        )

    return _run_consumer(
        consumer_name="Summarize",
        entity=EntityTypes.RESOURCE,
        description=EventDescriptions.CLEAN_UP_FINISHED,
        handler=handler,
    )


def consume_chunk_and_embed() -> int:
    """Chunk cleaned resource text and persist embeddings."""

    from kb.models import Chunk
    from kb.services import chromadb_service
    from kb.services import chunking as chunking_service

    def handler(event: Event) -> str:
        resource = get_object_or_404(Resource, id=event.entity_id)
        logger.info(f"Chunking and embedding text for Resource {resource.id}...")

        chunk_config = ChunkConfig.objects.first()
        if chunk_config:
            chunk_texts = chunking_service.chunk_text(
                resource.extracted_text, chunk_config.details
            )
            for index, text in enumerate(chunk_texts):
                try:
                    with transaction.atomic():
                        Chunk.objects.create(
                            text=text,
                            order=index,
                            resource=resource,
                            chunk_config=chunk_config,
                        )
                        chromadb_service.add_chunks(
                            resource.id, [text], start_index=index
                        )
                except Exception as exc:
                    logger.error(
                        f"Failed to process chunk {index} for resource {resource.id}: {exc}"
                    )

        return (
            f"Consumed 'clean up finished' event {event.id} for Resource "
            f"{resource.id} (chunked and embedded)"
        )

    return _run_consumer(
        consumer_name="Chunk and Embed Resource",
        entity=EntityTypes.RESOURCE,
        description=EventDescriptions.CLEAN_UP_FINISHED,
        handler=handler,
    )


def consume_extract_title_of_resource() -> int:
    """Extract a title from cleaned resource text."""

    system_prompt = (
        "Extract the exact title of the text provided. "
        "Only reply with the title and nothing else."
    )

    def handler(event: Event) -> str:
        resource = get_object_or_404(Resource, id=event.entity_id)
        logger.info(f"Calling LLM to extract title for Resource {resource.id}...")

        title_text = (
            f"MOCKED TITLE: {resource.extracted_text[:30]}"
            if _is_pytest_mode()
            else _call_llm(
                username="rkb-consumer-extract-title",
                system_prompt=system_prompt,
                message=resource.extracted_text[:500],
                fallback="Unknown Title",
                error_log_message="Error calling LLM for title extraction",
            )
        )

        resource.title = title_text.strip()
        resource.save()
        return (
            f"Consumed 'clean up finished' event {event.id} for Resource "
            f"{resource.id} (extracted title)"
        )

    return _run_consumer(
        consumer_name="Extract title of resource",
        entity=EntityTypes.RESOURCE,
        description=EventDescriptions.CLEAN_UP_FINISHED,
        handler=handler,
    )


def consume_extract_references() -> int:
    """Extract references from cleaned resource text."""

    system_prompt = (
        "Extract all references, citations, or mentions of other works, papers, "
        "or resources from the following text. "
        "For each reference, provide a clear description. "
        "Format the output as a bulleted list with each reference on a new line. "
        "Do not include any other text in your response."
    )

    def handler(event: Event) -> str:
        resource = get_object_or_404(Resource, id=event.entity_id)
        logger.info(f"Calling LLM to extract references for Resource {resource.id}...")

        if _is_pytest_mode():
            references = [f"MOCKED REFERENCE: {resource.extracted_text[:20]}"]
        else:
            llm_output = _call_llm(
                username="rkb-consumer-extract-references",
                system_prompt=system_prompt,
                message=resource.extracted_text,
                fallback="",
                error_log_message="Error calling LLM for references",
            )
            references = [
                line.strip().lstrip("-* ").strip()
                for line in llm_output.splitlines()
                if line.strip()
            ]

        for ref_desc in references:
            Reference.objects.create(resource=resource, description=ref_desc)

        return (
            f"Consumed 'clean up finished' event {event.id} for Resource "
            f"{resource.id} (extracted {len(references)} references)"
        )

    return _run_consumer(
        consumer_name="Extract references",
        entity=EntityTypes.RESOURCE,
        description=EventDescriptions.CLEAN_UP_FINISHED,
        handler=handler,
    )


def consume_check_kg_update() -> int:
    """Check whether active knowledge graph configs should be updated."""

    from django_llm_chat.models import Message

    system_prompt = (
        "Analyze the following user message and determine if the user "
        "is explicitly asking to update, refresh, or add information to the knowledge graph. "
        "Respond with exactly 'TRUE' if yes, or 'FALSE' if no."
    )

    def handler(event: Event) -> str | None:
        chat_id = int(event.entity_id)
        active_configs = KnowledgeGraphConfig.objects.filter(is_active=True)

        for config in active_configs:
            should_update = config.update_trigger == KnowledgeGraphUpdateTrigger.ALWAYS
            if config.update_trigger == KnowledgeGraphUpdateTrigger.LLM_INTENT:
                last_msg = (
                    Message.objects.filter(chat_id=chat_id, type="user")
                    .order_by("-date_created")
                    .first()
                )
                if last_msg:
                    if _is_pytest_mode():
                        should_update = "update" in last_msg.text.lower()
                    else:
                        llm_response = _call_llm(
                            username="rkb-consumer-kg-check",
                            system_prompt=system_prompt,
                            message=last_msg.text,
                            fallback="FALSE",
                            error_log_message="Error calling LLM for KG intent check",
                        )
                        should_update = llm_response.strip().upper() == "TRUE"

            if should_update:
                logger.info(
                    "Firing KNOWLEDGE_GRAPH_UPDATE_REQUESTED for config "
                    f"{config.id} in chat {chat_id}"
                )
                fire_event(
                    entity=EntityTypes.CHAT,
                    entity_id=f"{chat_id}:{config.id}",
                    description=EventDescriptions.KNOWLEDGE_GRAPH_UPDATE_REQUESTED,
                    triggered_by="Check KG Update",
                )

        return None

    return _run_consumer(
        consumer_name="Check KG Update",
        entity=EntityTypes.CHAT,
        description=EventDescriptions.CHAT_MESSAGE_SUBMITTED,
        handler=handler,
    )


def consume_update_knowledge_graph() -> int:
    """Run knowledge graph update packages for queued update events."""

    from django_llm_chat.models import Message
    from kb.services import chunking as chunking_service

    def handler(event: Event) -> None:
        chat_id_str, config_id_str = event.entity_id.split(":")
        chat_id = int(chat_id_str)
        config_id = int(config_id_str)

        config = get_object_or_404(KnowledgeGraphConfig, id=config_id)
        logger.info(
            f"Executing KG update for {config.package_name} on chat {chat_id}..."
        )

        if _is_pytest_mode():
            return None

        try:
            package = importlib.import_module(config.package_name)
        except ImportError as exc:
            logger.error(f"Failed to import KG package {config.package_name}: {exc}")
            return None

        if not hasattr(package, "run_update"):
            logger.error(
                f"Package {config.package_name} does not have 'run_update' function."
            )
            return None

        messages = Message.objects.filter(chat_id=chat_id).order_by("date_created")
        full_content = "\n\n".join(
            f"{message.type}: {message.text}" for message in messages if message.text
        )

        chunk_config = ChunkConfig.objects.first()
        if chunk_config and full_content:
            chunks = chunking_service.chunk_text(full_content, chunk_config.details)
        elif full_content:
            chunks = [full_content]
        else:
            chunks = []

        for index, chunk_text in enumerate(chunks):
            metadata = {
                "chat_id": chat_id,
                "config_id": config_id,
                "config_name": config.name,
                "chunk_index": index,
            }
            track_id = f"chat_{chat_id}_config_{config_id}_chunk_{index}"
            result = package.run_update(
                content=chunk_text,
                metadata=metadata,
                track_id=track_id,
            )
            if "error" in result:
                logger.error(
                    f"KG update failed for chat {chat_id} chunk {index}: "
                    f"{result.get('message', 'Unknown error')}"
                )

        return None

    return _run_consumer(
        consumer_name="Update Knowledge Graph",
        entity=EntityTypes.CHAT,
        description=EventDescriptions.KNOWLEDGE_GRAPH_UPDATE_REQUESTED,
        handler=handler,
    )


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
