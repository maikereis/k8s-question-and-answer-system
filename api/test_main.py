"""
Tests for main.py.

All external dependencies (Redis, SemanticCache, HFTextVectorizer, vLLM) are
stubbed via conftest.py.  Each test controls app.state directly after the
lifespan has run — no coupling to module-level globals.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from main import app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client():
    """Async HTTP client wired to the FastAPI app via ASGI transport.
    LifespanManager explicitly runs the app's lifespan (startup/shutdown),
    which populates app.state with the mocks from conftest.py."""
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_check_success(client):
    """Health returns 200 when Redis ping succeeds."""
    app.state.redis.ping.return_value = True

    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_check_failure(client):
    """Health returns 503 when Redis ping raises."""
    app.state.redis.ping.side_effect = Exception("Connection Error")

    response = await client.get("/health")

    assert response.status_code == 503
    assert "Redis unavailable" in response.json()["detail"]

    # Reset for other tests
    app.state.redis.ping.side_effect = None
    app.state.redis.ping.return_value = True


# ---------------------------------------------------------------------------
# /ask — Tier 1: exact cache hit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ask_exact_cache_hit(client):
    """Tier 1: exact Redis string match returns immediately; semantic cache never queried."""
    prompt = "Qual a voltagem da rede?"
    expected_answer = "A voltagem é 220V."

    app.state.redis.get.return_value = expected_answer

    response = await client.post("/ask", json={"prompt": prompt})

    assert response.status_code == 200
    assert response.json() == {"answer": expected_answer, "source": "exact_cache"}
    # SemanticCache.check must NOT have been called on an exact hit
    app.state.semantic_cache.check.assert_not_called()

    # Reset
    app.state.redis.get.return_value = None
    app.state.semantic_cache.check.reset_mock()


# ---------------------------------------------------------------------------
# /ask — Tier 2: semantic cache hit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ask_semantic_cache_hit(client):
    """Tier 2: no exact match, SemanticCache returns a semantically similar answer."""
    prompt = "Como economizar energia?"
    cached_answer = "Use lâmpadas LED."

    app.state.redis.get.return_value = None
    app.state.semantic_cache.check.return_value = [{"response": cached_answer}]

    response = await client.post("/ask", json={"prompt": prompt})

    assert response.status_code == 200
    assert response.json() == {"answer": cached_answer, "source": "semantic_cache"}
    # LLM must NOT have been called
    app.state.vllm_client.chat.completions.create.assert_not_called()

    # Reset
    app.state.semantic_cache.check.return_value = []
    app.state.vllm_client.chat.completions.create.reset_mock()


# ---------------------------------------------------------------------------
# /ask — Tier 3: full cache miss → LLM inference
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ask_llm_inference_miss(client):
    """Tier 3: no cache at all; LLM is called and result is written to both caches."""
    prompt = "O que é um disjuntor?"
    llm_answer = "Um dispositivo de proteção elétrica."

    app.state.redis.get.return_value = None
    app.state.semantic_cache.check.return_value = []

    mock_message = MagicMock()
    mock_message.content = llm_answer
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=mock_message)]
    app.state.vllm_client.chat.completions.create = AsyncMock(
        return_value=mock_response
    )

    response = await client.post("/ask", json={"prompt": prompt})

    assert response.status_code == 200
    assert response.json() == {"answer": llm_answer, "source": "llm_inference"}

    # Exact cache must have been written
    app.state.redis.setex.assert_called_once()
    setex_args = app.state.redis.setex.call_args[0]
    assert setex_args[2] == llm_answer

    # Semantic cache must have been written
    app.state.semantic_cache.store.assert_called_once()
    store_kwargs = app.state.semantic_cache.store.call_args
    assert store_kwargs.kwargs.get("prompt") == prompt or store_kwargs.args[0] == prompt

    # Reset
    app.state.redis.setex.reset_mock()
    app.state.semantic_cache.store.reset_mock()
    app.state.semantic_cache.check.return_value = []


# ---------------------------------------------------------------------------
# /ask — LLM error → 503
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ask_llm_error(client):
    """Tier 3: LLM call raises → 503 with informative detail."""
    app.state.redis.get.return_value = None
    app.state.semantic_cache.check.return_value = []
    app.state.vllm_client.chat.completions.create = AsyncMock(
        side_effect=Exception("vLLM Down")
    )

    response = await client.post("/ask", json={"prompt": "erro"})

    assert response.status_code == 503
    assert "Failed to reach LLM service" in response.json()["detail"]
