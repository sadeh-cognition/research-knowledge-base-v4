from loguru import logger

import events.consumers as consumers_pkg
from events.models import EntityTypes, Event, EventDescriptions
from kb.models import Resource


def consume_summarize() -> int:
    """Summarize cleaned resource text."""

    system_prompt = (
        "You are an assistant that summarizes text. "
        "Please provide a concise and informative summary of the following text."
    )

    def handler(event: Event) -> str:
        resource = consumers_pkg.get_object_or_404(Resource, id=event.entity_id)
        logger.info(f"Calling LLM to summarize text for Resource {resource.id}...")

        summary_text = (
            f"MOCKED SUMMARY: {resource.extracted_text}"
            if consumers_pkg._is_pytest_mode()
            else consumers_pkg._call_llm(
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

    return consumers_pkg._run_consumer(
        consumer_name="Summarize",
        entity=EntityTypes.RESOURCE,
        description=EventDescriptions.CLEAN_UP_FINISHED,
        handler=handler,
    )
