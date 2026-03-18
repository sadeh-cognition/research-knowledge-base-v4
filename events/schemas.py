from datetime import datetime
from ninja import Schema


class EventConsumerOut(Schema):
    id: int
    name: str


class EventOut(Schema):
    id: int
    entity: str
    entity_id: str
    entity_name: str | None = None
    description: str
    date_created: datetime


class EventConsumedOut(Schema):
    id: int
    event_id: int
    consumer: EventConsumerOut
    created_at: datetime
    status: str
    exception: str | None = None


class EventFlowOut(Schema):
    events: list[EventOut]
    consumers: list[EventConsumerOut]
    event_consumed: list[EventConsumedOut]
