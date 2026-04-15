# EnerGuia Q&A — Kubernetes-Native LLM Infrastructure

![Built with Kubernetes](https://img.shields.io/badge/Built%20with-Kubernetes-326CE5?logo=kubernetes&logoColor=white)
![Model](https://img.shields.io/badge/Model-EnerGuia--0.5B-FF6B35?logo=huggingface&logoColor=white)
![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white)
![Redis](https://img.shields.io/badge/Cache-Redis-DC382D?logo=redis&logoColor=white)
![vLLM](https://img.shields.io/badge/Inference-vLLM-6B4FBB?logoColor=white)

A production-ready, Kubernetes-native Q&A system powered by a fine-tuned Small Language Model (SLM) for answering questions about energy distribution in Brazil. Features semantic caching via Redis to minimize redundant LLM inference and maximize throughput.

---

## Architecture

The system is composed of **8 deployments** across the cluster:

| Component | Role | Replicas |
|---|---|---|
| `llm-app` | FastAPI backend — handles requests & semantic caching | 4 (prod) |
| `vllm-server` | vLLM inference server serving EnerGuia-0.5B | 1 |
| `redis-cache` | Vector store for embedding-based semantic cache | 1 |
| `prometheus` | Metrics scraping & storage | 1 |
| `grafana` | Monitoring dashboards | 1 |
| `model-preloader` | One-time Job to pre-download embedding model to shared PVC | — |

<img src=assets/qa_system_architecture_diagram.svg widht=500px height=500px>

**Semantic caching** uses `all-MiniLM-L6-v2` (Sentence Transformers) to embed queries into 384-dimensional vectors, stored and searched in Redis. Two queries that are semantically equivalent — even if worded differently — share a cached response, avoiding redundant inference.

---

## Model

The Q&A model, [`maikerdr/EnerGuia-0.5B`](https://huggingface.co/maikerdr/EnerGuia-0.5B), was trained using **LoRA (Low-Rank Adaptation)** on top of [`Qwen/Qwen2.5-0.5-Instruct`](https://huggingface.co/Qwen/Qwen2.5-0.5-Instruct) from Alibaba, chosen for its strong performance in Brazilian Portuguese.

It is served at runtime by **vLLM**, exposing an OpenAI-compatible `/v1` endpoint consumed by the FastAPI layer.

---

## Setup

### Prerequisites

- [Minikube](https://minikube.sigs.k8s.io/) with Docker driver
- `kubectl`, `helm`, `jq`
- NVIDIA GPU accessible via WSL2 (or native Linux)
- Hugging Face account with access token

---

### 0. Pre-pulling Images into Minikube (Recommended)

If you experience image pull errors inside the cluster (e.g. `ErrImagePull`, `ImagePullBackOff`) due to network restrictions or registry connectivity issues, you can pull images directly into Minikube's Docker daemon instead of relying on Kubernetes to fetch them at runtime.

Point your local Docker CLI at Minikube's internal Docker daemon, then pull the image as usual — it will land inside the cluster and be available without any network calls from Kubernetes:

```bash
# Point your shell's Docker CLI to Minikube's Docker daemon
eval $(minikube docker-env)

# Pull the desired image directly into Minikube
docker pull <image-name>:<tag>

# Examples:
docker pull ghcr.io/<your-org>/api:latest
docker pull ghcr.io/<your-org>/model-preloader:latest
docker pull vllm/vllm-openai:latest
docker pull redis:latest
```

> **Important:** Make sure your Kubernetes manifests set `imagePullPolicy: Never` (or `IfNotPresent`) for the affected containers, so Kubernetes uses the locally cached image instead of trying to pull it again from the registry.

```yaml
containers:
  - name: llm-app
    image: ghcr.io/<your-org>/api:latest
    imagePullPolicy: Never   # use the image already present in Minikube
```

To restore your shell's Docker CLI back to the host daemon when you're done:

```bash
eval $(minikube docker-env --unset)
```

---

### 1. Enable GPU Support

```bash
minikube addons enable nvidia-device-plugin

minikube delete --all --purge

minikube start \
  --driver=docker \
  --cpus=6 \
  --memory=12288 \
  --gpus=all \
  --mount \
  --mount-string="/usr/lib/wsl:/usr/lib/wsl" \
  --wait-timeout=15m

# Verify GPU is visible to Kubernetes
kubectl get nodes -o json | jq '.items[].status.allocatable["nvidia.com/gpu"]'
```

### 2. Install NVIDIA GPU Operator

```bash
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
helm repo update

helm install gpu-operator nvidia/gpu-operator \
  -n gpu-operator --create-namespace \
  --set driver.enabled=false \
  --set toolkit.enabled=true \
  --set operator.defaultRuntime=docker

# Wait for all pods to be ready (~5 min)
kubectl get pods -n gpu-operator -w

# Confirm GPU capacity
kubectl get nodes -o json | jq '.items[].status.capacity'

# Smoke test
kubectl run gpu-test \
  --image=nvidia/cuda:12.2.0-base-ubuntu22.04 \
  --restart=Never \
  -- nvidia-smi

kubectl get pods -w
kubectl logs gpu-test
kubectl delete pod gpu-test
```

---

### 3. Deploy — Development

```bash
# Create secrets
kubectl create secret generic grafana-secret \
  --from-literal=admin-password=<MY_VERY_SECRET> -n dev

kubectl create secret generic hf-token-secret \
  --from-literal=token=<HF_TOKEN> -n dev

# Create namespace
kubectl apply -f infra/overlays/dev/namespace.yaml

# Deploy with Kustomize
kubectl apply -k infra/overlays/dev

# Watch pods come up
kubectl get pods -n dev -w

# Expose services
minikube service dev-grafana-service -n dev
minikube service dev-app-service -n dev
```

### 4. Deploy — Production

```bash
# Create secrets
kubectl create secret generic grafana-secret \
  --from-literal=admin-password=<MY_VERY_SECRET> -n prod

kubectl create secret generic hf-token-secret \
  --from-literal=token=<HF_TOKEN> -n prod

# Create namespace
kubectl apply -f infra/overlays/prod/namespace.yaml

# Deploy with Kustomize
kubectl apply -k infra/overlays/prod

# Expose services
minikube service prod-grafana-service -n prod
minikube service prod-app-service -n prod
```

---

## Using the API

Once the app service is tunneled, access the **Swagger UI** at `http://localhost:<PORT>/docs`.

Click **`/ask`** → **Try it out** and submit:

```json
{
  "prompt": "Qual o prazo para a distribuidora realizar uma ligação nova?"
}
```

**Example response:**

```json
{
  "answer": "O prazo máximo para ligação nova é de 10 dias contados a partir da solicitação. No entanto, se a demanda estiver submetida à distribuidora, poderá ser liberada antes desse prazo.",
  "source": "llm_inference"
}
```

The `source` field indicates whether the response came from `exact_cache`, `semantic_cache`, or `llm_inference`.

---

## Monitoring

Access Grafana at the tunneled port. The admin password can be retrieved with:

```bash
kubectl get secret dev-grafana-secret -n dev \
  -o jsonpath="{.data.admin-password}" | base64 --decode
```

The **LLM API** dashboard tracks:

| Panel | Description |
|---|---|
| Request Rate | Requests/sec split by exact hit, semantic hit, and LLM inference |
| Cache Hit Rate | Exact, semantic, and combined hit rates over time |
| P50 / P90 / P99 Latency | Latency percentile stats |
| Latency Percentiles over Time | Trend view of all percentiles |
| Request Source Breakdown | Donut chart of cache vs inference traffic |
| Cumulative Request Totals | Lifetime counters |

Prometheus data is persisted via PVC (`prometheus-pvc.yaml`). The dashboard is provisioned automatically via `grafana-provisioning-configmap.yaml`.

---

## Configuration

Key environment variables for the `llm-app` deployment:

| Variable | Default | Description |
|---|---|---|
| `VLLM_URL` | `http://vllm-service:8000/v1` | vLLM inference endpoint |
| `REDIS_URL` | `redis://redis-service:6379` | Redis connection string |
| `SIMILARITY_THRESHOLD` | `0.85` | Cosine similarity cutoff for semantic cache hits |
| `SEMANTIC_CACHE_TTL` | `3600` | Cache entry TTL in seconds |
| `REDIS_VECTOR_DIM` | `384` | Embedding vector dimensions |
| `REDIS_VECTOR_DISTANCE` | `COSINE` | Distance metric for vector search |
| `EMBEDDINGS_MODEL` | `all-MiniLM-L6-v2` | Sentence Transformers model for query embedding |
| `MODEL_NAME` | `maikerdr/EnerGuia-0.5B` | LLM model identifier |

---

## Load Testing Results

| Metric | 600 Users | 1,000 Users |
|---|---|---|
| Peak Throughput | ~120 RPS | Degraded |
| P95 Latency | Acceptable | ~10 seconds |
| Error Rate | Low | Significantly elevated |

The system handled up to **600 concurrent users** with a peak of **120 RPS** before hitting saturation. At 1,000 users, P95 latency spiked to ~10 seconds with notable error rate increases. Early latency fluctuations are attributable to cache warming.

**Recommended next steps for scaling:**
- Horizontal scaling of `llm-app` replicas
- Resource limit tuning on the API layer
- Consider adding a second vLLM replica with tensor parallelism for GPU headroom

---

## CI/CD

Container images are built and published to GitHub Container Registry via GitHub Actions:

| Workflow | Image | Purpose |
|---|---|---|
| `api-ci.yaml` | `ghcr.io/.../api` | FastAPI application |
| `preloader-ci.yaml` | `ghcr.io/.../model-preloader` | Embedding model preloader |

---

## References

- Reis, M. (2024). [EnerGuia-0.5B](https://huggingface.co/maikerdr/EnerGuia-0.5B) — Hugging Face
- Reis, M. (2024). [k8s-question-and-answer-system](https://github.com/maikereis/k8s-question-and-answer-system) — GitHub
- Reimers, N., & Gurevych, I. (2019). [Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks](https://sbert.net/)
