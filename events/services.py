from events.models import DEFAULT_EVENT_TRIGGER, Event


def fire_event(
    entity: str,
    entity_id: str,
    description: str,
    *,
    triggered_by: str = DEFAULT_EVENT_TRIGGER,
) -> Event:
    """Helper function to create a new Event."""
    return Event.objects.create(
        entity=entity,
        entity_id=entity_id,
        description=description,
        triggered_by=triggered_by,
    )
