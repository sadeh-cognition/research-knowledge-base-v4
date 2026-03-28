import pytest
from conf.models import KnowledgeGraphUpdateTrigger
from events.models import ConsumptionStatus, Event, EntityTypes, EventDescriptions
from events.consumers import consume_check_kg_update, consume_update_knowledge_graph
from kb.models import KnowledgeGraphConfig
from kb.services.llm import LLMProvider
from django_llm_chat.models import Message, Chat


@pytest.mark.django_db
class TestKGConsumers:
    def test_check_kg_update_always(self):
        # Create config
        config = KnowledgeGraphConfig.objects.create(
            name="Test KG",
            update_trigger=KnowledgeGraphUpdateTrigger.ALWAYS,
            is_active=True,
        )

        # Create event
        chat = Chat.objects.create()
        Event.objects.create(
            entity=EntityTypes.CHAT,
            entity_id=str(chat.id),
            description=EventDescriptions.CHAT_MESSAGE_SUBMITTED,
        )

        count = consume_check_kg_update()
        assert count == 1

        # Verify it fired the next event
        next_event = Event.objects.filter(
            description=EventDescriptions.KNOWLEDGE_GRAPH_UPDATE_REQUESTED
        ).first()
        assert next_event is not None
        assert next_event.entity_id == f"{chat.id}:{config.id}"

    def test_check_kg_update_intent_true(self):
        from django.contrib.auth import get_user_model
        from kb.models import LLMConfig

        LLMConfig.objects.create(
            name="mock_llm",
            model_name="mock",
            provider=LLMProvider.LMSTUDIO,
            is_default=True,
        )
        User = get_user_model()
        user = User.objects.create(username="testuser_intent1")
        KnowledgeGraphConfig.objects.create(
            name="Test KG Intent",
            update_trigger=KnowledgeGraphUpdateTrigger.LLM_INTENT,
            is_active=True,
        )

        chat = Chat.objects.create()
        # "update" triggers TRUE in our mocked check
        Message.objects.create(
            chat=chat, type="user", text="Please update the graph", user=user
        )

        Event.objects.create(
            entity=EntityTypes.CHAT,
            entity_id=str(chat.id),
            description=EventDescriptions.CHAT_MESSAGE_SUBMITTED,
        )

        count = consume_check_kg_update()
        assert count == 1

        next_event = Event.objects.filter(
            description=EventDescriptions.KNOWLEDGE_GRAPH_UPDATE_REQUESTED
        ).first()
        assert next_event is not None

    def test_check_kg_update_intent_false(self):
        from django.contrib.auth import get_user_model
        from kb.models import LLMConfig

        LLMConfig.objects.create(
            name="mock_llm2",
            model_name="mock2",
            provider=LLMProvider.LMSTUDIO,
            is_default=True,
        )
        User = get_user_model()
        user = User.objects.create(username="testuser_intent2")
        KnowledgeGraphConfig.objects.create(
            name="Test KG Intent",
            update_trigger=KnowledgeGraphUpdateTrigger.LLM_INTENT,
            is_active=True,
        )

        chat = Chat.objects.create()
        Message.objects.create(
            chat=chat, type="user", text="Hello what is this?", user=user
        )

        Event.objects.create(
            entity=EntityTypes.CHAT,
            entity_id=str(chat.id),
            description=EventDescriptions.CHAT_MESSAGE_SUBMITTED,
        )

        count = consume_check_kg_update()
        assert count == 1

        next_event = Event.objects.filter(
            description=EventDescriptions.KNOWLEDGE_GRAPH_UPDATE_REQUESTED
        ).first()
        assert next_event is None

    def test_consume_update_knowledge_graph(self):
        config = KnowledgeGraphConfig.objects.create(
            name="Test KG", package_name="test_dummy_pkg", is_active=True
        )

        chat_id = 999
        event = Event.objects.create(
            entity=EntityTypes.CHAT,
            entity_id=f"{chat_id}:{config.id}",
            description=EventDescriptions.KNOWLEDGE_GRAPH_UPDATE_REQUESTED,
        )

        count = consume_update_knowledge_graph()
        assert count == 1

        # It's mocked so it won't actually fail import or execute
        assert (
            Event.objects.get(id=event.id).eventconsumed_set.first().status
            == ConsumptionStatus.OK
        )

    def test_consume_update_knowledge_graph_sends_full_chat_text_and_preserves_chunking(
        self, monkeypatch, django_user_model
    ):
        config = KnowledgeGraphConfig.objects.create(
            name="Test KG", package_name="test_dummy_pkg", is_active=True
        )
        chat = Chat.objects.create()
        user = django_user_model.objects.create(username="kg-full-chat-user")
        Message.objects.create(chat=chat, type="user", text="First message", user=user)
        Message.objects.create(
            chat=chat, type="assistant", text="Second reply", user=user
        )
        Message.objects.create(chat=chat, type="user", text="Third note", user=user)

        Event.objects.create(
            entity=EntityTypes.CHAT,
            entity_id=f"{chat.id}:{config.id}",
            description=EventDescriptions.KNOWLEDGE_GRAPH_UPDATE_REQUESTED,
        )

        full_chat_text = (
            "user: First message\n\nassistant: Second reply\n\nuser: Third note"
        )
        calls = []

        class DummyPackage:
            @staticmethod
            def run_update(*, content, metadata, track_id):
                calls.append(
                    {
                        "content": content,
                        "metadata": metadata,
                        "track_id": track_id,
                    }
                )
                return {"status": "ok"}

        monkeypatch.setattr("events.consumers._is_pytest_mode", lambda: False)
        monkeypatch.setattr(
            "events.consumers.importlib.import_module",
            lambda package_name: DummyPackage(),
        )
        monkeypatch.setattr(
            "kb.services.chunking.chunk_text",
            lambda text, details: ["chunk one", "chunk two"],
        )

        count = consume_update_knowledge_graph()

        assert count == 1
        assert calls == [
            {
                "content": "chunk one",
                "metadata": {
                    "chat_id": chat.id,
                    "config_id": config.id,
                    "config_name": config.name,
                    "chunk_index": 0,
                    "full_chat_text": full_chat_text,
                },
                "track_id": f"chat_{chat.id}_config_{config.id}_chunk_0",
            },
            {
                "content": "chunk two",
                "metadata": {
                    "chat_id": chat.id,
                    "config_id": config.id,
                    "config_name": config.name,
                    "chunk_index": 1,
                    "full_chat_text": full_chat_text,
                },
                "track_id": f"chat_{chat.id}_config_{config.id}_chunk_1",
            },
        ]
