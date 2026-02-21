# GLiNER-PII

A self-hosted, GPU-accelerated REST API for detecting Personally Identifiable Information (PII) in text, powered by the [`knowledgator/gliner-pii-base-v1.0`](https://huggingface.co/knowledgator/gliner-pii-base-v1.0) model and served via FastAPI.

## What is GLiNER?

[GLiNER](https://github.com/urchade/GLiNER) (Generalist and Lightweight Named Entity Recognition) is a compact NER model that can identify arbitrary entity types at inference time — no task-specific fine-tuning required. Instead of being limited to a fixed set of labels, you provide the labels you want at request time and the model finds them.

`gliner-pii-base-v1.0` is a variant fine-tuned specifically for PII detection tasks such as names, emails, phone numbers, addresses, and more.

## Features

- **Zero-config PII detection** — pass any text and a list of labels, get entities back
- **Flexible labels** — detect any combination of PII types per request
- **GPU-accelerated** — runs on CUDA 12.4 via the official PyTorch 2.5.1 Docker image
- **Offline-capable** — model weights are baked into the Docker image at build time
- **Production-ready** — health check endpoint, `restart: unless-stopped`, uvicorn ASGI server

## API

### `GET /health`
Returns `{"status": "ok"}` — used by the Docker health check.

### `POST /predict`

**Request body:**
```json
{
  "text": "My name is Miguel and my email is miguel@example.com",
  "labels": ["person", "email", "phone number", "location"],
  "threshold": 0.3
}
```

| Field | Type | Default | Description |
|---|---|---|---|
| `text` | string | required | The input text to scan for PII |
| `labels` | list of strings | `["person", "email", "phone number", "location"]` | Entity types to detect |
| `threshold` | float | `0.3` | Minimum confidence score (0–1) to include an entity |

**Response:**
```json
{
  "entities": [
    {"text": "Miguel", "label": "person", "start": 11, "end": 17, "score": 0.91},
    {"text": "miguel@example.com", "label": "email", "start": 34, "end": 52, "score": 0.97}
  ]
}
```

## Requirements

- Docker + Docker Compose
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) (for GPU passthrough)
- A CUDA-capable GPU

## Getting Started

```bash
# Build the image (downloads model weights during build)
docker compose build

# Start the API server
docker compose up -d

# Check it's running
curl http://localhost:5000/health

# Run a prediction
curl -X POST http://localhost:5000/predict \
     -H "Content-Type: application/json" \
     -d '{"text": "My name is Miguel and my email is miguel@example.com"}'
```

## Configuration

To use the lighter/faster edge model, swap the model name in both `main.py` and the `Dockerfile` bake step:

```
gliner-pii-base-v1.0  →  gliner-pii-edge-v1.0
```

## Project Structure

```
.
├── main.py             # FastAPI app
├── requirements.txt    # Python dependencies
├── Dockerfile          # CUDA-enabled container build
└── docker-compose.yml  # Orchestration with GPU passthrough
```
