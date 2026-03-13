import pytest
import traceback
from model_bakery import baker
from django.conf import settings
from events.models import (
    EventConsumed,
    ConsumptionStatus,
    EntityTypes,
    EventDescriptions,
)
from events.services import fire_event
from events.consumers import (
    consume_clean_up_extracted_text,
    get_or_create_consumer,
    consume_summarize,
)

pytestmark = pytest.mark.django_db


def test_status_ok_on_success(monkeypatch):
    resource = baker.make("kb.Resource", extracted_text="Messy text")
    fire_event(
        entity=EntityTypes.RESOURCE,
        entity_id=str(resource.id),
        description=EventDescriptions.TEXT_EXTRACTED,
    )

    baker.make(
        "kb.LLMConfig",
        name="default",
        is_default=True,
        provider="groq",
        model_name="llama-3.1-8b-instant",
    )

    consume_clean_up_extracted_text()

    consumer = get_or_create_consumer("Clean up extracted text")
    consumed = EventConsumed.objects.get(
        consumer=consumer, event__entity_id=str(resource.id)
    )

    assert consumed.status == ConsumptionStatus.OK
    assert consumed.exception is None


def test_status_error_on_failure(monkeypatch):
    resource = baker.make("kb.Resource", extracted_text="Messy text")
    event = fire_event(
        entity=EntityTypes.RESOURCE,
        entity_id=str(resource.id),
        description=EventDescriptions.TEXT_EXTRACTED,
    )

    baker.make(
        "kb.LLMConfig",
        name="default",
        is_default=True,
        provider="groq",
        model_name="llama-3.1-8b-instant",
    )

    # Force a failure in the consumer
    import events.consumers

    def mock_fail(*args, **kwargs):
        raise ValueError("Simulated failure")

    monkeypatch.setattr("events.consumers.get_object_or_404", mock_fail)

    consume_clean_up_extracted_text()

    consumer = get_or_create_consumer("Clean up extracted text")
    consumed = EventConsumed.objects.get(consumer=consumer, event=event)

    assert consumed.status == ConsumptionStatus.ERROR
    assert "ValueError: Simulated failure" in consumed.exception
    assert "traceback" in consumed.exception.lower()


def test_retry_failed_setting_false(monkeypatch, settings):
    settings.EVENT_CONSUMER_RETRY_FAILED = False

    resource = baker.make("kb.Resource", extracted_text="Messy text")
    event = fire_event(
        entity=EntityTypes.RESOURCE,
        entity_id=str(resource.id),
        description=EventDescriptions.TEXT_EXTRACTED,
    )

    baker.make("kb.LLMConfig", is_default=True)

    # First run fails
    import events.consumers

    monkeypatch.setattr(
        "events.consumers.get_object_or_404",
        lambda *a, **k: exec('raise ValueError("Fail 1")'),
    )
    consume_clean_up_extracted_text()

    consumer = get_or_create_consumer("Clean up extracted text")
    consumed = EventConsumed.objects.get(consumer=consumer, event=event)
    assert consumed.status == ConsumptionStatus.ERROR

    # Second run should skip it because retry is False
    # If it's skipped, count should be 0 and no second call to get_object_or_404
    monkeypatch.setattr(
        "events.consumers.get_object_or_404",
        lambda *a, **k: exec('raise ValueError("Fail 2")'),
    )
    count = consume_clean_up_extracted_text()
    assert count == 0

    consumed.refresh_from_db()
    assert "Fail 1" in consumed.exception
    assert "Fail 2" not in consumed.exception


def test_retry_failed_setting_true(monkeypatch, settings):
    settings.EVENT_CONSUMER_RETRY_FAILED = True

    resource = baker.make("kb.Resource", extracted_text="Messy text")
    event = fire_event(
        entity=EntityTypes.RESOURCE,
        entity_id=str(resource.id),
        description=EventDescriptions.TEXT_EXTRACTED,
    )

    baker.make("kb.LLMConfig", is_default=True)

    # First run fails
    import events.consumers

    def fail1(*a, **k):
        raise ValueError("Fail 1")

    monkeypatch.setattr("events.consumers.get_object_or_404", fail1)
    consume_clean_up_extracted_text()

    consumer = get_or_create_consumer("Clean up extracted text")
    consumed = EventConsumed.objects.get(consumer=consumer, event=event)
    assert consumed.status == ConsumptionStatus.ERROR

    # Second run should retry it because retry is True
    # We mock it to succeed this time
    monkeypatch.setattr("events.consumers.get_object_or_404", lambda *a, **k: resource)
    count = consume_clean_up_extracted_text()
    assert count == 1

    consumed.refresh_from_db()
    assert consumed.status == ConsumptionStatus.OK
    assert consumed.exception is None
