from django.test import override_settings
from model_bakery import baker

from events.consumers import consume_clean_up_extracted_text, consume_summarize
from events.models import (
    ConsumptionStatus,
    EntityTypes,
    Event,
    EventConsumed,
    EventConsumer,
    EventDescriptions,
)
from kb.models import ResourceType


def test_consume_clean_up_extracted_text_updates_resource_and_fires_followup_event(
    db,
):
    resource = baker.make(
        "kb.Resource",
        url="https://example.com/test-paper",
        resource_type=ResourceType.PAPER,
        extracted_text="This is test content from a paper.",
    )
    event = baker.make(
        Event,
        entity=EntityTypes.RESOURCE,
        entity_id=str(resource.id),
        description=EventDescriptions.TEXT_EXTRACTED,
    )

    processed = consume_clean_up_extracted_text()

    resource.refresh_from_db()

    assert processed == 1
    assert (
        resource.extracted_text
        == "MOCKED CLEANED TEXT: This is test content from a paper."
    )
    assert (
        EventConsumed.objects.get(
            event=event,
            consumer__name="Clean up extracted text",
        ).status
        == ConsumptionStatus.OK
    )
    assert Event.objects.filter(
        entity=EntityTypes.RESOURCE,
        entity_id=str(resource.id),
        description=EventDescriptions.CLEAN_UP_FINISHED,
    ).exists()


@override_settings(EVENT_CONSUMER_RETRY_FAILED=True)
def test_consume_summarize_retries_failed_events_before_new_ones(db):
    first_resource = baker.make(
        "kb.Resource",
        url="https://example.com/first",
        resource_type=ResourceType.PAPER,
        extracted_text="first resource text",
    )
    second_resource = baker.make(
        "kb.Resource",
        url="https://example.com/second",
        resource_type=ResourceType.PAPER,
        extracted_text="second resource text",
    )

    first_event = baker.make(
        Event,
        entity=EntityTypes.RESOURCE,
        entity_id=str(first_resource.id),
        description=EventDescriptions.CLEAN_UP_FINISHED,
    )
    second_event = baker.make(
        Event,
        entity=EntityTypes.RESOURCE,
        entity_id=str(second_resource.id),
        description=EventDescriptions.CLEAN_UP_FINISHED,
    )
    consumer = baker.make(EventConsumer, name="Summarize")

    baker.make(
        EventConsumed,
        event=first_event,
        consumer=consumer,
        status=ConsumptionStatus.OK,
    )
    baker.make(
        EventConsumed,
        event=second_event,
        consumer=consumer,
        status=ConsumptionStatus.ERROR,
        exception="boom",
    )

    processed = consume_summarize()

    first_resource.refresh_from_db()
    second_resource.refresh_from_db()

    assert processed == 1
    assert first_resource.summary == ""
    assert second_resource.summary == "MOCKED SUMMARY: second resource text"
    assert (
        EventConsumed.objects.get(
            event=second_event,
            consumer=consumer,
        ).status
        == ConsumptionStatus.OK
    )
