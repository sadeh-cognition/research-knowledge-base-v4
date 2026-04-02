from loguru import logger

import events.consumers as consumers_pkg
from conf.models import ChunkConfig, KnowledgeGraphConfig
from events.models import EntityTypes, Event, EventDescriptions


def consume_update_knowledge_graph() -> int:
    """Run knowledge graph update packages for queued update events."""

    from django_llm_chat.models import Message
    from kb.services import chunking as chunking_service

    def handler(event: Event) -> None:
        chat_id_str, config_id_str = event.entity_id.split(":")
        chat_id = int(chat_id_str)
        config_id = int(config_id_str)

        config = consumers_pkg.get_object_or_404(KnowledgeGraphConfig, id=config_id)
        logger.info(
            f"Executing KG update for {config.package_name} on chat {chat_id}..."
        )

        if consumers_pkg._is_pytest_mode():
            return None

        try:
            package = consumers_pkg.importlib.import_module(config.package_name)
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

        if not full_content:
            return None

        chunk_config = ChunkConfig.objects.first()
        if chunk_config:
            chunks = chunking_service.chunk_text(full_content, chunk_config.details)
        else:
            chunks = [full_content]

        for index, chunk_text in enumerate(chunks):
            metadata = {
                "chat_id": chat_id,
                "config_id": config_id,
                "config_name": config.name,
                "chunk_index": index,
                "full_chat_text": full_content,
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

    return consumers_pkg._run_consumer(
        consumer_name="Update Knowledge Graph",
        entity=EntityTypes.CHAT,
        description=EventDescriptions.KNOWLEDGE_GRAPH_UPDATE_REQUESTED,
        handler=handler,
    )
