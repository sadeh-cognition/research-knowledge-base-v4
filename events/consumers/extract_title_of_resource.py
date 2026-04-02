from loguru import logger

import events.consumers as consumers_pkg
from events.models import EntityTypes, Event, EventDescriptions
from kb.models import Resource


def consume_extract_title_of_resource() -> int:
    """Extract a title from cleaned resource text."""

    system_prompt = (
        "Extract the exact title of the text provided. "
        "Only reply with the title and nothing else."
    )

    def handler(event: Event) -> str:
        resource = consumers_pkg.get_object_or_404(Resource, id=event.entity_id)
        logger.info(f"Calling LLM to extract title for Resource {resource.id}...")

        title_text = (
            f"MOCKED TITLE: {resource.extracted_text[:30]}"
            if consumers_pkg._is_pytest_mode()
            else consumers_pkg._call_llm(
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

    return consumers_pkg._run_consumer(
        consumer_name="Extract title of resource",
        entity=EntityTypes.RESOURCE,
        description=EventDescriptions.CLEAN_UP_FINISHED,
        handler=handler,
    )
