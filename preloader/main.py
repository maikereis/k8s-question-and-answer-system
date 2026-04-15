import logging
import os
import sys
from sentence_transformers import SentenceTransformer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def main():
    # Load settings from environment variables (provided by K8s Job)
    cache_dir = "/model-cache"
    embeddings_model = os.environ.get("EMBEDDINGS_MODEL", "all-MiniLM-L6-v2")

    # Idempotency check: Don't download if we've already finished this model
    marker_path = os.path.join(
        cache_dir, ".downloaded", embeddings_model.replace("/", "_")
    )

    if os.path.exists(marker_path):
        logger.info("Model '%s' is already cached. Skipping.", embeddings_model)
        return

    logger.info("Starting download for: %s", embeddings_model)
    try:
        # SentenceTransformer uses SENTENCE_TRANSFORMERS_HOME and HF_HOME env vars
        # automatically to decide where to save these files.
        SentenceTransformer(embeddings_model)

        # Create the success marker
        os.makedirs(os.path.dirname(marker_path), exist_ok=True)
        with open(marker_path, "w") as f:
            f.write("completed")

        logger.info("Successfully cached '%s'", embeddings_model)
    except Exception as e:
        logger.exception("Error during model download: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
