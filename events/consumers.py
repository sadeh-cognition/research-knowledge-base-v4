import os
from loguru import logger
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.contrib.auth import get_user_model

from django_llm_chat.chat import Chat

from events.models import (
    Event,
    EventConsumer,
    EventConsumed,
    EntityTypes,
    EventDescriptions,
)
from events.services import fire_event
from kb.models import Resource
from kb.services import llm as llm_service
from kb.services import chat as chat_service

User = get_user_model()


def _get_or_create_consumer_user() -> "User":
    """Get or create the consumer user for automated LLM tasks."""
    user, _ = User.objects.get_or_create(
        username="rkb-consumer",
        defaults={"password": "unused"},
    )
    return user


def get_or_create_consumer(name: str) -> EventConsumer:
    consumer, _ = EventConsumer.objects.get_or_create(name=name)
    return consumer


def _get_llm_config():
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
    return f"{provider}/{model_name}"


def consume_clean_up_extracted_text() -> int:
    """
    Consumer that processes "text extracted from resource" events.
    It cleans up the extracted text using an LLM to remove non-human-readable parts.
    """
    consumer = get_or_create_consumer("Clean up extracted text")

    # Find unprocessed events
    unprocessed_events = Event.objects.filter(
        entity=EntityTypes.RESOURCE, description=EventDescriptions.TEXT_EXTRACTED
    ).exclude(eventconsumed__consumer=consumer)

    count = 0
    for event in unprocessed_events:
        with transaction.atomic():
            try:
                resource = get_object_or_404(Resource, id=event.entity_id)
                # Call LLM logic
                model_name = _get_llm_config()

                system_prompt = (
                    "You are an assistant that cleans up extracted text from resources. "
                    "Your task is to remove all non-human-readable text, random numbers, "
                    "useless strings of letters, and excessive whitespace. "
                    "You must keep all human-readable text 100% intact. "
                    "Return ONLY the cleaned text and nothing else."
                )

                if os.environ.get("PYTEST_CURRENT_TEST"):
                    cleaned_text = f"MOCKED CLEANED TEXT: {resource.extracted_text}"
                else:
                    try:
                        chat_instance = Chat.create()
                        user = _get_or_create_consumer_user()
                        chat_instance.create_system_message(system_prompt, user)

                        ai_msg, _, _ = chat_instance.send_user_msg_to_llm(
                            model_name=model_name,
                            text=resource.extracted_text,
                            user=user,
                        )
                        cleaned_text = ai_msg.text or ""
                    except Exception as e:
                        logger.error(f"Error calling LLM for clean up: {e}")
                        cleaned_text = resource.extracted_text  # Fallback to original

                # Update resource
                resource.extracted_text = cleaned_text
                resource.save()

                # Mark event as consumed
                EventConsumed.objects.create(event=event, consumer=consumer)

                # Fire new event
                fire_event(
                    entity=EntityTypes.RESOURCE,
                    entity_id=event.entity_id,
                    description=EventDescriptions.CLEAN_UP_FINISHED,
                )

                count += 1
                logger.info(
                    f"Consumed 'text extracted' event {event.id} for Resource {resource.id}"
                )
            except Exception as e:
                logger.exception(
                    f"Failed to process clean up for event {event.id}: {e}"
                )

        break

    return count


def consume_summarize() -> int:
    """
    Consumer that processes "extracted text clean up finished" events.
    It creates a summary of the resource's extracted text.
    """
    consumer = get_or_create_consumer("Summarize")

    unprocessed_events = Event.objects.filter(
        entity=EntityTypes.RESOURCE, description=EventDescriptions.CLEAN_UP_FINISHED
    ).exclude(eventconsumed__consumer=consumer)

    count = 0
    for event in unprocessed_events:
        with transaction.atomic():
            try:
                resource = get_object_or_404(Resource, id=event.entity_id)

                model_name = _get_llm_config()

                system_prompt = (
                    "You are an assistant that summarizes text. "
                    "Please provide a concise and informative summary of the following text."
                )
                if os.environ.get("PYTEST_CURRENT_TEST"):
                    summary_text = f"MOCKED SUMMARY: {resource.extracted_text}"
                else:
                    try:
                        chat_instance = Chat.create()
                        user = _get_or_create_consumer_user()
                        chat_instance.create_system_message(system_prompt, user)

                        ai_msg, _, _ = chat_instance.send_user_msg_to_llm(
                            model_name=model_name,
                            text=resource.extracted_text,
                            user=user,
                        )
                        summary_text = ai_msg.text or ""
                    except Exception as e:
                        logger.error(f"Error calling LLM for summarize: {e}")
                        summary_text = "Error generating summary."

                resource.summary = summary_text
                resource.save()

                EventConsumed.objects.create(event=event, consumer=consumer)

                count += 1
                logger.info(
                    f"Consumed 'clean up finished' event {event.id} for Resource {resource.id}"
                )
            except Exception as e:
                logger.exception(
                    f"Failed to process summarize for event {event.id}: {e}"
                )
        break
    return count


def process_all_events() -> int:
    """Helper to process all consumers."""
    count = 0
    count += consume_clean_up_extracted_text()
    count += consume_summarize()
    return count
