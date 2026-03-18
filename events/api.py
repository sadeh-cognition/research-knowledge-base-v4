from ninja import Router
from events.models import Event, EventConsumer, EventConsumed
from events.schemas import EventFlowOut
from kb.models import Resource
from django_llm_chat.models import Chat

events_router = Router(tags=["events"])


@events_router.get("/flow/", response=EventFlowOut)
def get_event_flow(request):
    events = list(Event.objects.order_by("-date_created")[:100])
    consumers = list(EventConsumer.objects.all())
    # Only get event consumptions for the fetched events
    event_ids = [e.id for e in events]
    event_consumed = list(EventConsumed.objects.filter(event_id__in=event_ids))

    # Pre-fetch resources and chats to populate entity_names
    resource_ids = [
        int(e.entity_id)
        for e in events
        if e.entity == "resource" and e.entity_id.isdigit()
    ]
    chat_ids = []

    for e in events:
        if e.entity == "chat":
            if ":" in e.entity_id:  # chat_id:config_id
                chat_id_part = e.entity_id.split(":")[0]
                if chat_id_part.isdigit():
                    chat_ids.append(int(chat_id_part))
            elif e.entity_id.isdigit():
                chat_ids.append(int(e.entity_id))

    resources = {
        r.id: r.title or r.url for r in Resource.objects.filter(id__in=resource_ids)
    }
    chats = {c.id: f"Chat {c.id}" for c in Chat.objects.filter(id__in=chat_ids)}

    for e in events:
        if e.entity == "resource" and e.entity_id.isdigit():
            e.entity_name = resources.get(int(e.entity_id))
        elif e.entity == "chat":
            c_id = None
            if ":" in e.entity_id:
                chat_id_part = e.entity_id.split(":")[0]
                if chat_id_part.isdigit():
                    c_id = int(chat_id_part)
            elif e.entity_id.isdigit():
                c_id = int(e.entity_id)
            if c_id:
                e.entity_name = chats.get(c_id)

    return {"events": events, "consumers": consumers, "event_consumed": event_consumed}
