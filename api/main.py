import asyncio
import hashlib
import logging
import os
import sys
import time
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from openai import AsyncOpenAI
from prometheus_client import Counter, Histogram, make_asgi_app
from pydantic import BaseModel
from redis import Redis
from redisvl.extensions.cache.llm import SemanticCache
from redisvl.utils.vectorize import HFTextVectorizer

load_dotenv()


class Query(BaseModel):
    prompt: str


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("app")


# --- Metrics ---

EXACT_HITS = Counter("cache_exact_hits_total", "Exact string match hits")
SEMANTIC_HITS = Counter("cache_semantic_hits_total", "Semantic similarity hits")
CACHE_MISSES = Counter("cache_misses_total", "Total cache misses")
LATENCY = Histogram(
    "request_latency_seconds",
    "Request latency",
    buckets=[0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10],
)


def get_env_or_exit(var_name: str, default=None, required=False):
    value = os.getenv(var_name, default)
    if required and not value:
        raise RuntimeError(f"Missing required environment variable: {var_name}")
    return value


def init_redis(url: str) -> Redis:
    client = Redis.from_url(url, decode_responses=True)
    client.ping()
    return client


def init_vllm_client(base_url: str) -> AsyncOpenAI:
    return AsyncOpenAI(base_url=base_url, api_key="token")


# --- Lifespan ---


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_url = get_env_or_exit("REDIS_URL", required=True)
    vllm_url = get_env_or_exit("VLLM_URL", required=True)
    embeddings_model = get_env_or_exit("EMBEDDINGS_MODEL", "all-MiniLM-L6-v2")
    model_device = get_env_or_exit("MODEL_DEVICE", "cpu")

    app.state.model_name = get_env_or_exit("MODEL_NAME", "maikerdr/EnerGuia-0.5B")
    app.state.system_prompt = get_env_or_exit(
        "SYSTEM_PROMPT",
        "Você é um assistente especialista em direitos do consumidor de energia elétrica no Brasil, "
        "com base nas normas da ANEEL e na legislação vigente. Responda de forma clara, objetiva e empática. "
        "Quando a pergunta estiver fora do seu domínio de conhecimento, responda taxativamente com "
        '"Não posso responder essa pergunta!"',
    )
    app.state.semantic_cache_ttl = int(get_env_or_exit("SEMANTIC_CACHE_TTL", "3600"))
    similarity_threshold = float(get_env_or_exit("SIMILARITY_THRESHOLD", "0.85"))

    # SemanticCache uses distance, not similarity: distance = 1 - similarity (COSINE)
    distance_threshold = 1.0 - similarity_threshold

    try:
        app.state.redis = init_redis(redis_url)
    except Exception as e:
        logger.error(f"FATAL: Could not connect to Redis at {redis_url}: {e}")
        sys.exit(1)

    try:
        logger.info("Initializing SemanticCache...")
        vectorizer = HFTextVectorizer(model=embeddings_model, device=model_device)
        app.state.semantic_cache = SemanticCache(
            name="llm_cache",
            redis_client=app.state.redis,
            vectorizer=vectorizer,
            distance_threshold=distance_threshold,
            ttl=app.state.semantic_cache_ttl,
        )
        logger.info("Application startup complete.")
    except Exception as e:
        logger.error(f"FATAL: Error during lifespan startup: {e}")
        sys.exit(1)

    app.state.vllm_client = init_vllm_client(vllm_url)

    yield

    logger.info("Shutting down... closing Redis connections.")
    app.state.redis.close()


app = FastAPI(lifespan=lifespan)


# --- Routes ---


@app.get("/health")
async def health(request: Request):
    try:
        request.app.state.redis.ping()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Redis unavailable: {e}") from e


@app.post("/ask")
async def ask(request: Request, query: Query):
    state = request.app.state
    start_ts = time.time()
    prompt_clean = query.prompt.strip()

    # TIER 1: Exact match
    prompt_hash = hashlib.sha256(prompt_clean.encode()).hexdigest()
    exact_match = state.redis.get(f"exact:{prompt_hash}")

    if exact_match:
        EXACT_HITS.inc()
        LATENCY.observe(time.time() - start_ts)
        return {"answer": exact_match, "source": "exact_cache"}

    # TIER 2: Semantic match — check() encodes + queries internally
    loop = asyncio.get_event_loop()
    semantic_matches = await loop.run_in_executor(
        None, lambda: state.semantic_cache.check(prompt=prompt_clean, num_results=1)
    )

    if semantic_matches:
        SEMANTIC_HITS.inc()
        answer = semantic_matches[0]["response"]
        LATENCY.observe(time.time() - start_ts)
        return {"answer": answer, "source": "semantic_cache"}

    # TIER 3: Inference
    CACHE_MISSES.inc()
    try:
        response = await state.vllm_client.chat.completions.create(
            model=state.model_name,
            messages=[
                {"role": "system", "content": state.system_prompt},
                {"role": "user", "content": prompt_clean},
            ],
        )
        answer = response.choices[0].message.content

        # Store in exact cache
        state.redis.setex(f"exact:{prompt_hash}", state.semantic_cache_ttl, answer)

        # Store in semantic cache (handles encoding + vector storage + TTL)
        await loop.run_in_executor(
            None,
            lambda: state.semantic_cache.store(prompt=prompt_clean, response=answer),
        )

        LATENCY.observe(time.time() - start_ts)
        return {"answer": answer, "source": "llm_inference"}

    except Exception as e:
        logger.error(f"Inference error: {e}")
        raise HTTPException(
            status_code=503, detail=f"Failed to reach LLM service: {e}"
        ) from e


# Metrics endpoint
app.mount("/metrics", make_asgi_app())

if __name__ == "__main__":
    port = int(os.getenv("APP_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
