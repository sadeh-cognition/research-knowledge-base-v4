import pytest
from django.utils import timezone
from model_bakery import baker
from django.core.management import call_command

from events.models import Event, EventConsumer, EventConsumed, EntityTypes, EventDescriptions
from events.services import fire_event
from events.consumers import consume_clean_up_extracted_text, consume_summarize, get_or_create_consumer
from kb.models import Resource, LLMConfig

pytestmark = pytest.mark.django_db

def test_fire_event():
    event = fire_event(
        entity=EntityTypes.RESOURCE,
        entity_id="123",
        description=EventDescriptions.TEXT_EXTRACTED
    )
    assert event.id is not None
    assert event.entity == EntityTypes.RESOURCE
    assert event.entity_id == "123"
    assert event.description == EventDescriptions.TEXT_EXTRACTED
    
    # Test str
    assert str(event) == "Resource 123: Text Extracted From Resource"

def test_consumer_models():
    event = baker.make("events.Event")
    consumer = baker.make("events.EventConsumer", name="Test Consumer")
    
    consumed = EventConsumed.objects.create(event=event, consumer=consumer)
    
    assert consumed.id is not None
    assert str(consumer) == "Test Consumer"
    assert f"Event {event.id} consumed by Test Consumer" in str(consumed)

def test_clean_up_extracted_text_consumer(monkeypatch):
    resource = baker.make("kb.Resource", extracted_text="Some messy   text\n123")
    
    # Fire event
    event = fire_event(
        entity=EntityTypes.RESOURCE,
        entity_id=str(resource.id),
        description=EventDescriptions.TEXT_EXTRACTED
    )
    
    baker.make("kb.LLMConfig", name="default", is_default=True, provider="openrouter", model_name="liquid/lfm-2.5-1.2b-instruct:free")
    
    # Run consumer 
    count = consume_clean_up_extracted_text()
    
    # In tests, the PYTEST_CURRENT_TEST var is set, so it uses the mocked text
    assert count == 1
    
    resource.refresh_from_db()
    assert "MOCKED CLEANED TEXT: " in resource.extracted_text
    
    # Verify it created the next event
    next_events = Event.objects.filter(
        entity=EntityTypes.RESOURCE, 
        entity_id=str(resource.id),
        description=EventDescriptions.CLEAN_UP_FINISHED
    )
    assert next_events.count() == 1
    
    # Verify it marked the initial event as consumed
    consumer = get_or_create_consumer("Clean up extracted text")
    assert EventConsumed.objects.filter(event=event, consumer=consumer).exists()
    
    # Verify running again does nothing (idempotency)
    count_again = consume_clean_up_extracted_text()
    assert count_again == 0

def test_summarize_consumer():
    resource = baker.make("kb.Resource", extracted_text="Cleaned up text here")
    
    # Fire event
    event = fire_event(
        entity=EntityTypes.RESOURCE,
        entity_id=str(resource.id),
        description=EventDescriptions.CLEAN_UP_FINISHED
    )
    
    baker.make("kb.LLMConfig", name="default", is_default=True, provider="openrouter", model_name="liquid/lfm-2.5-1.2b-instruct:free")
    
    count = consume_summarize()
    
    assert count == 1
    
    resource.refresh_from_db()
    assert "MOCKED SUMMARY: " in resource.summary
    
    consumer = get_or_create_consumer("Summarize")
    assert EventConsumed.objects.filter(event=event, consumer=consumer).exists()

    count_again = consume_summarize()
    assert count_again == 0

def test_run_consumers_command():
    resource1 = baker.make("kb.Resource", extracted_text="Text 1")
    resource2 = baker.make("kb.Resource", extracted_text="Text 2")
    
    fire_event(entity=EntityTypes.RESOURCE, entity_id=str(resource1.id), description=EventDescriptions.TEXT_EXTRACTED)
    fire_event(entity=EntityTypes.RESOURCE, entity_id=str(resource2.id), description=EventDescriptions.CLEAN_UP_FINISHED)
    
    baker.make("kb.LLMConfig", name="default", is_default=True, provider="openrouter", model_name="liquid/lfm-2.5-1.2b-instruct:free")
    
    # Run command with --once
    call_command("run_consumers", once=True)
    
    resource1.refresh_from_db()
    resource2.refresh_from_db()
    
    assert "MOCKED CLEANED TEXT: " in resource1.extracted_text
    assert "MOCKED SUMMARY: " in resource2.summary
