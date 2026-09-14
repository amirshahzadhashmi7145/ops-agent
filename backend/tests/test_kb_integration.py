import os
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.models.kb import KbProcessingStatus, KbReference
from app.services.kb_ingestion import process_reference
from app.services.kb_retrieval import search_knowledge_base

pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL required for KB integration tests",
)


@pytest.fixture
def db_session() -> Session:
    engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


@pytest.mark.asyncio
async def test_ingest_ready_and_search_respects_enabled(db_session: Session):
    reference = KbReference(
        title="Return Policy",
        raw_text="Customers may return devices within 30 days of purchase.",
        content_hash="pending",
        enabled=True,
        processing_status=KbProcessingStatus.queued,
        created_by="test@example.com",
    )
    db_session.add(reference)
    db_session.commit()
    db_session.refresh(reference)

    formatted = {
        "summary": "30-day return policy for devices.",
        "markdown": "# Return Policy\n\nCustomers may return devices within 30 days of purchase.",
    }
    fake_vectors = [[0.1] * 384]

    class FakeEmbedder:
        model_name = "test-embedder"

        def embed_documents(self, texts):
            return fake_vectors[: len(texts)]

        def embed_query(self, text):
            return [0.1] * 384

    with (
        patch("app.services.kb_ingestion.format_reference_text", new=AsyncMock(return_value=formatted)),
        patch("app.services.kb_ingestion.get_embedding_provider", return_value=FakeEmbedder()),
        patch("app.services.kb_retrieval.get_embedding_provider", return_value=FakeEmbedder()),
    ):
        await process_reference(db_session, reference.id, force=True)

        db_session.refresh(reference)
        assert reference.processing_status == KbProcessingStatus.ready
        assert reference.summary == formatted["summary"]

        # Searches must run INSIDE the patch scope so the query is embedded with
        # the same FakeEmbedder as the stored chunk. Otherwise the real embedder
        # ranks unrelated dev-DB articles above this fixture's fake-embedded chunk,
        # making the test depend on whatever else lives in the shared database.
        # This fixture's fake-embedded chunk is an exact match (distance 0), so it
        # ranks first. Assertions target THIS reference specifically so the test is
        # robust to any other articles present in the shared database.
        ref_id = str(reference.id)
        matches = search_knowledge_base(db_session, "return policy")
        assert matches[0]["title"] == "Return Policy"
        assert any(m["reference_id"] == ref_id for m in matches)

        reference.enabled = False
        db_session.commit()

        disabled_matches = search_knowledge_base(db_session, "return policy")
        assert all(m["reference_id"] != ref_id for m in disabled_matches)

    reference.active = False
    db_session.commit()
