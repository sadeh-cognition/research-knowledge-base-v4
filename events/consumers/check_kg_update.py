from loguru import logger

import events.consumers as consumers_pkg
from events.models import EntityTypes, Event, EventDescriptions
from kb.models import KnowledgeGraphConfig


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
            should_update = (
                config.update_trigger
                == consumers_pkg.KnowledgeGraphUpdateTrigger.ALWAYS
            )
            if (
                config.update_trigger
                == consumers_pkg.KnowledgeGraphUpdateTrigger.LLM_INTENT
            ):
                last_msg = (
                    Message.objects.filter(chat_id=chat_id, type="user")
                    .order_by("-date_created")
                    .first()
                )
                if last_msg:
                    if consumers_pkg._is_pytest_mode():
                        should_update = "update" in last_msg.text.lower()
                    else:
                        llm_response = consumers_pkg._call_llm(
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
                consumers_pkg.fire_event(
                    entity=EntityTypes.CHAT,
                    entity_id=f"{chat_id}:{config.id}",
                    description=EventDescriptions.KNOWLEDGE_GRAPH_UPDATE_REQUESTED,
                    triggered_by="Check KG Update",
                )

        return None

    return consumers_pkg._run_consumer(
        consumer_name="Check KG Update",
        entity=EntityTypes.CHAT,
        description=EventDescriptions.CHAT_MESSAGE_SUBMITTED,
        handler=handler,
    )
