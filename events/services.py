from events.models import Event

def fire_event(entity: str, entity_id: str, description: str) -> Event:
    """Helper function to create a new Event."""
    return Event.objects.create(
        entity=entity,
        entity_id=entity_id,
        description=description,
    )
