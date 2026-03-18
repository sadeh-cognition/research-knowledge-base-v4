import pytest
from ninja.testing import TestClient
from kb.api import api
from events.models import (
    Event,
    EventConsumer,
    EventConsumed,
    EntityTypes,
    EventDescriptions,
    ConsumptionStatus,
)
from model_bakery import baker
from events.schemas import EventFlowOut


@pytest.fixture
def api_client():
    return TestClient(api)


@pytest.mark.django_db
def test_event_flow_api(api_client):
    event1 = baker.make(
        Event, entity=EntityTypes.RESOURCE, description=EventDescriptions.TEXT_EXTRACTED
    )
    event2 = baker.make(
        Event,
        entity=EntityTypes.RESOURCE,
        description=EventDescriptions.CLEAN_UP_FINISHED,
    )

    consumer1 = baker.make(EventConsumer, name="Clean up text")
    consumer2 = baker.make(EventConsumer, name="Summarize")

    baker.make(
        EventConsumed, event=event1, consumer=consumer1, status=ConsumptionStatus.OK
    )
    baker.make(
        EventConsumed, event=event2, consumer=consumer2, status=ConsumptionStatus.OK
    )

    response = api_client.get("/events/flow/")
    assert response.status_code == 200

    # Validate with schema
    data = EventFlowOut.parse_raw(response.content)

    assert len(data.events) == 2
    assert len(data.consumers) == 2
    assert len(data.event_consumed) == 2

    event_ids = [e.id for e in data.events]
    assert event1.id in event_ids
    assert event2.id in event_ids
