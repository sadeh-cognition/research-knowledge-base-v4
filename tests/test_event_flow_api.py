import pytest
from ninja.testing import TestClient
from kb.api import api
from conf.models import KnowledgeGraphUpdateTrigger
from kb.models import KnowledgeGraphConfig
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
    assert all(e.triggered_by for e in data.events)


@pytest.mark.django_db
def test_request_knowledge_graph_update_creates_events_for_active_configs(api_client):
    active_config = KnowledgeGraphConfig.objects.create(
        name="Active KG",
        update_trigger=KnowledgeGraphUpdateTrigger.ALWAYS,
        is_active=True,
    )
    KnowledgeGraphConfig.objects.create(
        name="Inactive KG",
        update_trigger=KnowledgeGraphUpdateTrigger.ALWAYS,
        is_active=False,
    )

    response = api_client.post("/events/knowledge-graph-update-requested/123/")
    assert response.status_code == 200

    data = response.json()
    assert data["chat_id"] == 123
    assert data["config_ids"] == [active_config.id]
    assert len(data["event_ids"]) == 1

    event = Event.objects.get(id=data["event_ids"][0])
    assert event.entity == EntityTypes.CHAT
    assert event.entity_id == f"123:{active_config.id}"
    assert event.description == EventDescriptions.KNOWLEDGE_GRAPH_UPDATE_REQUESTED
    assert event.triggered_by == "TUI /kg-update"
