from loguru import logger

import events.consumers as consumers_pkg
from conf.models import ChunkConfig
from events.models import EntityTypes, Event, EventDescriptions
from kb.models import Chunk, Resource
from kb.services import chromadb_service
from kb.services import chunking as chunking_service


def consume_chunk_and_embed() -> int:
    """Chunk cleaned resource text and persist embeddings."""

    def handler(event: Event) -> str:
        resource = consumers_pkg.get_object_or_404(Resource, id=event.entity_id)
        logger.info(f"Chunking and embedding text for Resource {resource.id}...")

        chunk_config = ChunkConfig.objects.first()
        if chunk_config:
            chunk_texts = chunking_service.chunk_text(
                resource.extracted_text, chunk_config.details
            )
            for index, text in enumerate(chunk_texts):
                try:
                    with consumers_pkg.transaction.atomic():
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

    return consumers_pkg._run_consumer(
        consumer_name="Chunk and Embed Resource",
        entity=EntityTypes.RESOURCE,
        description=EventDescriptions.CLEAN_UP_FINISHED,
        handler=handler,
    )
