# EnerGuia — RAG vs Fine-Tuning Benchmark

A research pipeline that compares two approaches for answering Brazilian electricity consumer-rights questions: **Retrieval-Augmented Generation (RAG)** using a vector index, and **supervised fine-tuning (LoRA)** of a 0.5B model — then benchmarks both head-to-head.

---

## Project Structure

```
.
├── data/
│   ├── datasets/
│   │   ├── finetunning.jsonl   # Fine-tuning training examples
│   │   ├── eval.jsonl          # Evaluation split
│   │   └── benchmark.jsonl     # Shared benchmark (question / key_facts / type)
│   └── cache/
│       ├── rag.json            # Incremental RAG inference results
│       └── finetuned.json      # Incremental fine-tuned inference results
├── model/
│   └── results_lora/           # LoRA adapter checkpoints + tokenizer
└── notebook.ipynb              # Main pipeline (cells described below)
```

---

## Pipeline Overview

### 1. RAG Baseline

A static knowledge base covering ANEEL regulations (REN 1.000/2021, Lei 15.235/2025, Marco Legal da Geração Distribuída, etc.) is chunked recursively into ~400-character segments with 50-character overlap.

Chunks are embedded with `all-MiniLM-L6-v2` (via `sentence-transformers`) and indexed in a **FAISS `IndexFlatIP`** (cosine similarity after L2 normalisation). At query time, the top-3 retrieved chunks are prepended to the prompt before calling the base model.

### 2. LoRA Fine-Tuning

The base model (`Qwen/Qwen2.5-0.5B-Instruct`) is fine-tuned with **LoRA (PEFT)** — no quantisation — on 251 instruction-following examples in the `messages` chat format.

Key hyperparameters:

| Parameter | Value |
|---|---|
| LoRA rank (r) | 16 |
| LoRA alpha | 32 |
| Target modules | `q_proj`, `k_proj`, `v_proj`, `o_proj` |
| Epochs | 5 |
| Effective batch size | 16 (2 × 8 grad. accum.) |
| Learning rate | 2e-4 (cosine, warmup 5%) |
| Optimizer | `paged_adamw_8bit` |
| Precision | fp16 |

Training is handled by `SFTTrainer` (TRL). The adapter is pushed to `maikerdr/EnerGuia-0.5B` on the Hugging Face Hub.

### 3. Benchmark & Evaluation

Both approaches are run on the same `benchmark.jsonl` dataset. Each question has a `type` field (`general`, `out_of_domain`, etc.) and a `key_facts` list.

Scoring is keyword-based:
- **In-domain questions:** `score = matched key-facts / total key-facts`
- **Out-of-domain questions:** `score = 1.0` if the response contains the expected refusal phrase, `0.0` otherwise

Results are cached incrementally so interrupted runs resume safely.

### 4. Visualisation

A 4-panel Matplotlib figure is generated:

1. **Overall accuracy** — bar chart of mean key-facts score per approach
2. **Score by question category** — grouped bar chart
3. **Mean latency** — inference time per approach (seconds)
4. **Response stability** — per-question score line plot

---

## Setup

```bash
pip install transformers peft trl datasets sentence-transformers faiss-cpu matplotlib numpy torch
```

For GPU inference and `paged_adamw_8bit`, also install:

```bash
pip install bitsandbytes accelerate
```

Set your Hugging Face token:

```bash
export HF_TOKEN=hf_...
```

---

## Running

Open and run `notebook.ipynb` top to bottom. Each section is independently resumable via the JSON caches in `data/cache/`.

To run only the benchmark (skipping training):

1. Make sure `data/cache/rag.json` and `data/cache/finetuned.json` are complete.
2. Jump directly to the **Evaluation** cell.


---

## Model Card

See [`maikerdr/EnerGuia-0.5B`](https://huggingface.co/maikerdr/EnerGuia-0.5B) on Hugging Face for the full model card.
