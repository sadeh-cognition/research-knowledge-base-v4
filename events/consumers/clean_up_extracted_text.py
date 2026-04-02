from loguru import logger

import events.consumers as consumers_pkg
from events.models import EntityTypes, Event, EventDescriptions
from kb.models import Resource


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
        resource = consumers_pkg.get_object_or_404(Resource, id=event.entity_id)
        logger.info(
            f"Calling LLM to clean up extracted text for Resource {resource.id}..."
        )

        cleaned_text = (
            f"MOCKED CLEANED TEXT: {resource.extracted_text}"
            if consumers_pkg._is_pytest_mode()
            else consumers_pkg._call_llm(
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
        consumers_pkg.fire_event(
            entity=EntityTypes.RESOURCE,
            entity_id=event.entity_id,
            description=EventDescriptions.CLEAN_UP_FINISHED,
            triggered_by="Clean up extracted text",
        )

        return f"Consumed 'text extracted' event {event.id} for Resource {resource.id}"

    return consumers_pkg._run_consumer(
        consumer_name="Clean up extracted text",
        entity=EntityTypes.RESOURCE,
        description=EventDescriptions.TEXT_EXTRACTED,
        handler=handler,
    )
