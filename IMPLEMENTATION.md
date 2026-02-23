# GLiNER-PII Implementation Details

## 1. Service Purpose

This service exposes a minimal REST API for PII extraction from text.

- Framework: FastAPI
- Model runtime: GLiNER (`knowledgator/gliner-pii-base-v1.0`)
- Transport: HTTP/JSON
- Deployment target: Docker container with optional NVIDIA GPU passthrough

The application is intentionally small: one health endpoint and one prediction endpoint.

## 2. Source Layout

- `main.py`: API application, request schema, model loading, and inference route
- `requirements.txt`: Python runtime dependencies
- `Dockerfile`: container build process and model pre-download step
- `docker-compose.yml`: local orchestration, port mapping, GPU reservation, and health check
- `README.md`: usage overview and quickstart

## 3. Application Boot Sequence (`main.py`)

### 3.1 FastAPI app construction

At import time:

1. `app = FastAPI(title="GLiNER-PII API")` creates the ASGI application.
2. `model = GLiNER.from_pretrained("knowledgator/gliner-pii-base-v1.0")` loads model weights.

Important behavior:

- Model loading happens during module import, before serving requests.
- If model loading fails (network/cache/corrupt artifacts), process startup fails.
- The model object is global and reused for all requests in the process.

### 3.2 Request schema

`PIIRequest` (Pydantic model) defines request validation:

- `text: str` (required)
- `labels: List[str]` with default:
  - `["person", "email", "phone number", "location"]`
- `threshold: float` with default `0.3`

Validation that currently exists:

- Type validation from Pydantic (`text` must be string, etc.)

Validation that does **not** currently exist:

- No explicit range check for `threshold` (e.g., 0.0 to 1.0)
- No size limits for `text`
- No normalization/enforcement for label vocabulary

### 3.3 Endpoints

#### `GET /health`

- Returns static JSON: `{"status": "ok"}`
- Used by Docker Compose health check

#### `POST /predict`

Flow:

1. FastAPI parses and validates JSON body into `PIIRequest`.
2. Route calls:
   - `model.predict_entities(request.text, request.labels, threshold=request.threshold)`
3. Returned entities are wrapped as:
   - `{"entities": entities}`

Output shape depends on GLiNER library response (typically entity text, label, span offsets, score).

## 4. Inference Runtime Characteristics

### 4.1 Concurrency model

- Route is declared `async`, but model inference call is synchronous CPU/GPU work.
- Inference runs in request handler context and can block worker execution.
- Throughput and latency therefore depend mainly on:
  - number of Uvicorn workers (currently default single worker)
  - model/device performance
  - input length and number of labels

### 4.2 Model lifecycle

- Single global model instance per process.
- No lazy loading or warmup endpoint.
- No explicit teardown hooks required in this implementation.

### 4.3 Error behavior

Current behavior:

- Unhandled runtime errors bubble up to FastAPI and return 500 responses.
- No custom exception mapping for model/inference failures.

## 5. Dependency Stack (`requirements.txt`)

- `fastapi`: API framework and request/response modeling
- `uvicorn[standard]`: ASGI server
- `gliner`: model wrapper/inference API
- `transformers<4.49`: constrained version to preserve compatibility with current GLiNER setup

## 6. Container Build and Runtime (`Dockerfile`)

### 6.1 Base image

- `pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime`

This provides:

- Python runtime
- CUDA libraries
- cuDNN runtime
- PyTorch aligned to CUDA in image

### 6.2 Build steps

1. Set workdir `/app`
2. Copy `requirements.txt`
3. Install Python dependencies
4. Copy `main.py`
5. Run preload command:
   - `GLiNER.from_pretrained('knowledgator/gliner-pii-base-v1.0')`
6. Expose port `5000`
7. Start server:
   - `uvicorn main:app --host 0.0.0.0 --port 5000`

### 6.3 Why preload at build time

The explicit preload step bakes model artifacts into the image layer cache:

- Reduces cold-start download dependency at runtime
- Enables offline inference if image is already built and deployed

Tradeoff:

- Larger image size
- Build depends on network access to model host

## 7. Compose Orchestration (`docker-compose.yml`)

Service: `pii-api`

- `build: .` and tagged image `gliner-pii-api`
- `container_name: pii-server`
- Port map `5000:5000`
- Restart policy `unless-stopped`

GPU reservation block:

- Requests one NVIDIA GPU device with `capabilities: [gpu]`

Health check:

- Command: `curl -f http://localhost:5000/health`
- Interval: 30s
- Timeout: 10s
- Retries: 3

Operational note:

- In some Compose environments, `deploy.resources` semantics vary outside Swarm.
- If GPU is not exposed correctly, inference may still run on CPU (slower), depending on backend availability.

## 8. Request/Response Contract

### 8.1 Example request

```json
{
  "text": "My name is Miguel and my email is miguel@example.com",
  "labels": ["person", "email", "phone number", "location"],
  "threshold": 0.3
}
```

### 8.2 Example response

```json
{
  "entities": [
    {
      "text": "Miguel",
      "label": "person",
      "start": 11,
      "end": 17,
      "score": 0.91
    },
    {
      "text": "miguel@example.com",
      "label": "email",
      "start": 34,
      "end": 52,
      "score": 0.97
    }
  ]
}
```

Entity shape is determined by GLiNER internals; consumers should parse defensively.

## 9. End-to-End Sequence

1. Client sends HTTP `POST /predict` with JSON body.
2. FastAPI validates body into `PIIRequest`.
3. Handler invokes GLiNER with text, labels, and threshold.
4. GLiNER returns extracted entities.
5. FastAPI serializes `{"entities": ...}` and returns HTTP 200.

## 10. Current Gaps and Improvement Targets

These are not defects in the current minimal design, but common production hardening areas:

- Input constraints:
  - enforce `threshold` bounds
  - limit max text length
  - reject empty text/labels
- Reliability:
  - add structured error handling around inference
  - add startup readiness checks beyond static health
- Performance:
  - benchmark CPU vs GPU and tune worker count
  - consider batching strategy for high throughput
- Security:
  - add authentication/authorization if exposed beyond trusted network
  - add request logging with PII-safe redaction policy
- Observability:
  - metrics for latency, throughput, error rates
  - tracing/correlation IDs
- API stability:
  - version endpoints (e.g., `/v1/predict`)
  - define strict response schema

## 11. Summary

The implemented service is a straightforward inference microservice:

- one globally loaded GLiNER PII model
- one prediction route with configurable labels and threshold
- one health route for orchestration
- CUDA-capable containerization with model artifacts preloaded at build time

It is suitable as a lightweight internal PII extraction API and a strong base for production hardening.
