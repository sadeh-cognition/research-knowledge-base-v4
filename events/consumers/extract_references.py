from loguru import logger

import events.consumers as consumers_pkg
from events.models import EntityTypes, Event, EventDescriptions
from kb.models import Reference, Resource


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
        resource = consumers_pkg.get_object_or_404(Resource, id=event.entity_id)
        logger.info(f"Calling LLM to extract references for Resource {resource.id}...")

        if consumers_pkg._is_pytest_mode():
            references = [f"MOCKED REFERENCE: {resource.extracted_text[:20]}"]
        else:
            llm_output = consumers_pkg._call_llm(
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

    return consumers_pkg._run_consumer(
        consumer_name="Extract references",
        entity=EntityTypes.RESOURCE,
        description=EventDescriptions.CLEAN_UP_FINISHED,
        handler=handler,
    )
