"""
conftest.py runs before any test module is imported.
We set the required env vars and stub out every external dependency
(Redis, SemanticCache, HFTextVectorizer, AsyncOpenAI) so that:
  - `import main` never fails due to missing env vars
  - no real network/model connections are attempted in tests
  - app.state is populated with controllable mocks via the lifespan
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

# --- 1. Env vars must be set before `main` is imported ---
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("VLLM_URL", "http://localhost:8000/v1")


# --- 2. Build reusable mock factories ---


def make_redis_mock():
    m = MagicMock()
    m.ping.return_value = True
    m.get.return_value = None
    m.setex.return_value = True
    m.close.return_value = None
    return m


def make_semantic_cache_mock():
    m = MagicMock()
    m.check.return_value = []
    m.store.return_value = None
    return m


def make_vllm_client_mock(answer: str = "default answer"):
    mock_message = MagicMock()
    mock_message.content = answer
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    client = MagicMock()
    client.chat = MagicMock()
    client.chat.completions = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=mock_response)
    return client


# --- 3. Patch external calls so lifespan never does real I/O ---
#    - init_redis       → avoids real Redis TCP connection
#    - HFTextVectorizer → avoids downloading/loading the embedding model
#    - SemanticCache    → avoids RedisVL index creation
#    - init_vllm_client → avoids real OpenAI/vLLM connection

_redis_mock = make_redis_mock()
_semantic_cache_mock = make_semantic_cache_mock()
_vllm_client_mock = make_vllm_client_mock()

_patches = [
    patch("main.init_redis", return_value=_redis_mock),
    patch("main.HFTextVectorizer", return_value=MagicMock()),
    patch("main.SemanticCache", return_value=_semantic_cache_mock),
    patch("main.init_vllm_client", return_value=_vllm_client_mock),
]


def pytest_configure(config):
    for p in _patches:
        p.start()


def pytest_unconfigure(config):
    for p in _patches:
        p.stop()
