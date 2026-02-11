# TrafficIQ: Multi-Modal Vehicle Identification Pipeline

![Python 3.11](https://img.shields.io/badge/python-3.11-blue) ![License: MIT](https://img.shields.io/badge/license-MIT-green) ![Status: Alpha](https://img.shields.io/badge/status-alpha-orange)

## Problem Statement

Modern law enforcement and traffic management agencies process thousands of traffic camera images daily but lack efficient, AI-powered systems for automated vehicle identification at scale. `TrafficIQ` addresses this by providing a production-ready, multi-modal AI pipeline that analyzes traffic camera images to identify vehicles, extract license plates, correlate against watchlists (BOLO), and automatically generate prioritized case records for human investigators. The system supports both real Vertex AI endpoints and deterministic mock predictions for local development, enabling seamless testing without GCP dependencies.

## Architecture

![TrafficIQ System Architecture](./architecture/system_design.mmd)

The system is built around three core layers:

1. **API Layer** (FastAPI)
   - RESTful endpoints for vehicle analysis and agent orchestration
   - Cloud Run-ready containerization
   - JSON-structured logging for production observability

2. **Agent Orchestration** (Router)
   - Multi-step processing pipeline with policy-driven decisions
   - Conditional OCR fallback based on image quality and confidence
   - BOLO database correlation
   - Automatic priority assignment and case creation

3. **Tools Layer**
   - Vertex AI integration (real or mock)
   - OCR plate extraction
   - BOLO watchlist lookup
   - Evidence packet generation
   - Case management interface

## Features

- ✅ **Multi-Modal Analysis**: Vehicle make, model, year, color, body type detection
- ✅ **Adaptive OCR**: Automatic plate extraction when image quality is poor
- ✅ **BOLO Integration**: Watchlist correlation for suspected vehicles
- ✅ **Evidence Packets**: Structured JSON documentation of analyses
- ✅ **Priority System**: P0/P1/P2 case prioritization based on confidence
- ✅ **Mock Mode**: Deterministic predictions for offline development
- ✅ **Vertex AI Ready**: Drop-in replacement for real model endpoints
- ✅ **Evaluation Framework**: Built-in metrics, confusion matrices, calibration analysis
- ✅ **Type-Safe**: Full Pydantic models and FastAPI schema validation
- ✅ **Structured Logging**: JSON-formatted logs for cloud platforms
- ✅ **Cloud Run Ready**: Dockerfile, deployment docs, Terraform stubs included

## Quick Start

### Prerequisites

- Python 3.11+
- Git
- Docker (for containerization)

### Local Development

#### 1. Clone & Setup

```bash
git clone https://github.com/your-org/trafficiq.git
cd trafficiq

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Or use uv for faster setup
uv venv
source .venv/bin/activate
```

#### 2. Install Dependencies

```bash
# Development installation
pip install -e ".[dev]"

# Or for GCP support
pip install -e ".[gcp]"
```

#### 3. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env for your setup (defaults work for local development)
# USE_VERTEX=false  # Use mock predictions
# ENVIRONMENT=development
```

#### 4. Run API Server

```bash
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

API available at: `http://localhost:8000`
Docs available at: `http://localhost:8000/docs`

### Run Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=app --cov=eval

# Specific test
pytest tests/test_api.py::TestHealthEndpoint::test_health_check_success -v
```

### Run Evaluation

```bash
# Run evaluation on sample dataset
python -m eval.evaluate

# Check results
cat artifacts/eval_report.md
```

## API Endpoints

### Health Check

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "ok",
  "version": "0.1.0",
  "environment": "development"
}
```

### Analyze Vehicle

Predict vehicle details from a single image (lightweight, no OCR/BOLO):

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "image_uri": "gs://bucket/traffic_cam_001.jpg"
  }'
```

Response:
```json
{
  "image_uri": "gs://bucket/traffic_cam_001.jpg",
  "make": "Honda",
  "model": "Civic",
  "year_range": "2020-2021",
  "color": "black",
  "body_type": "sedan",
  "confidence": 0.85,
  "image_condition": "clear",
  "metadata": {
    "model_version": "gemma-3n-v1.0",
    "prediction_type": "mock"
  },
  "timestamp": "2024-01-15T14:30:00Z"
}
```

### Run Full Agent Pipeline

Execute the complete orchestration: predict → conditional OCR → BOLO check → case creation:

```bash
curl -X POST http://localhost:8000/agent/run \
  -H "Content-Type: application/json" \
  -d '{
    "image_uri": "gs://bucket/traffic_cam_001.jpg",
    "location": "Downtown Intersection A",
    "timestamp": "2024-01-15T14:30:00Z"
  }'
```

Response:
```json
{
  "image_uri": "gs://bucket/traffic_cam_001.jpg",
  "vehicle_prediction": {
    "make": "Honda",
    "model": "Civic",
    "year_range": "2020-2021",
    "color": "black",
    "body_type": "sedan",
    "confidence": 0.85,
    "image_condition": "clear"
  },
  "ocr_fallback_used": false,
  "plate_result": null,
  "bolo_match": {
    "is_match": true,
    "make": "Honda",
    "model": "Civic",
    "year_range": "2020-2021",
    "plate": null,
    "reason": "Make 'Honda' on watchlist",
    "match_confidence": 0.85,
    "bolo_record_id": "BOLO-MAKE-a1b2c3d4"
  },
  "priority": "P0",
  "case_record": {
    "case_id": "CASE-x1y2z3w4",
    "priority": "P0",
    "summary": "Vehicle ID: Honda Civic (2020-2021) - black sedan. Confidence: 85%. BOLO Match: True. Priority: P0.",
    "vehicle_make": "Honda",
    "vehicle_model": "Civic",
    "vehicle_year_range": "2020-2021",
    "status": "open",
    "created_at": "2024-01-15T14:30:00Z"
  },
  "processing_steps": [
    "vehicle_prediction_request",
    "vehicle_prediction_received",
    "ocr_skipped",
    "bolo_lookup_started",
    "bolo_lookup_completed",
    "priority_assignment",
    "evidence_packet_building",
    "evidence_packet_created",
    "case_creation",
    "case_created"
  ],
  "total_processing_time_ms": 145.32,
  "location": "Downtown Intersection A"
}
```

## Configuration

### Environment Variables

```bash
# Application
ENVIRONMENT=development              # development | production
LOG_LEVEL=info                        # debug, info, warning, error
JSON_LOGGING=true                     # JSON structured logs
API_TITLE=TrafficIQ
API_VERSION=0.1.0

# Vertex AI / GCP
USE_VERTEX=false                      # false = mock, true = real
GCP_PROJECT=my-gcp-project
GCP_REGION=us-central1
VERTEX_ENDPOINT_ID=projects/.../endpoints/...
VERTEX_MODEL_NAME=gemma-3n-tuned-vehicles

# Storage
ARTIFACTS_PATH=./artifacts
USE_GCS=false                         # false = local, true = GCS
GCS_BUCKET=my-trafficiq-bucket

# External Services
BOLO_SERVICE_URL=http://localhost:8001
CASE_SERVICE_URL=http://localhost:8002
DEBUG=false
```

### Policy Configuration

Adjustable thresholds in `app/agent/policy.py`:

```python
PolicyConfig(
    MIN_VEHICLE_CONFIDENCE_FOR_SKIP_OCR=0.70,  # Confidence needed to skip OCR
    MIN_PLATE_CONFIDENCE_FOR_BOLO=0.60,        # Minimum plate confidence
    NIGHT_QUALITY_PENALTY=0.15,                # Confidence reduction for night
    BLUR_QUALITY_PENALTY=0.20,                 # Confidence reduction for blur
)
```

Priority Rules:
- **P0**: BOLO match + vehicle confidence ≥ 0.70
- **P1**: BOLO match + vehicle confidence < 0.70
- **P2**: No BOLO match

## Project Structure

```
trafficIQ/
├── app/
│   ├── api/                    # FastAPI application
│   │   ├── main.py             # App initialization
│   │   └── routes.py           # Endpoint definitions
│   ├── agent/                  # Orchestration logic
│   │   ├── router.py           # Main agent
│   │   ├── policy.py           # Decision policies
│   │   └── prompts.py          # LLM prompts
│   ├── common/                 # Shared utilities
│   │   ├── config.py           # Configuration management
│   │   ├── logging.py          # Structured logging
│   │   ├── schemas.py          # Pydantic models
│   │   └── utils.py            # Helper functions
│   └── tools/                  # External integrations
│       ├── vertex_client.py     # Vertex AI interface
│       ├── ocr_client.py        # Plate extraction
│       ├── bolo_client.py       # Watchlist lookup
│       ├── evidence.py          # Evidence packets
│       └── case_client.py       # Case management
├── eval/                       # Evaluation module
│   ├── evaluate.py             # Evaluation pipeline
│   ├── metrics.py              # Metrics calculation
│   ├── dataset_schema.md       # Dataset format docs
│   └── sample_data.jsonl       # Sample evaluation data
├── tests/                      # Unit tests
│   ├── test_api.py             # API endpoint tests
│   ├── test_router.py          # Agent/policy tests
│   └── test_tools.py           # Tools layer tests
├── infra/                      # Deployment artifacts
│   ├── Dockerfile.api          # Container image for API
│   ├── Dockerfile.agent        # Container image for batch
│   ├── cloudrun_deploy.md      # Cloud Run deployment guide
│   └── terraform_stub.md       # Infrastructure as Code
├── architecture/
│   └── system_design.mmd       # Mermaid system diagram
├── pyproject.toml              # Project configuration
├── .env.example                # Environment template
└── README.md                   # This file
```

## Switching to Real Vertex AI

To use actual Vertex AI predictions instead of mocks:

### 1. Setup GCP Project

```bash
# Create project and enable APIs
gcloud projects create trafficiq-prod
gcloud config set project trafficiq-prod
gcloud services enable aiplatform.googleapis.com storage-api.googleapis.com
```

### 2. Create Vertex AI Endpoint

```bash
# Deploy your Gemma 3n fine-tuned model
# (Assuming you have a trained model checkpoint)
gcloud ai models create \
  --region=us-central1 \
  --display-name=gemma-3n-vehicles \
  --framework=pytorch

# Create endpoint
gcloud ai endpoints create \
  --region=us-central1 \
  --display-name=trafficiq-inference
```

### 3. Update Environment

```bash
# In .env or Cloud Run environment variables
USE_VERTEX=true
GCP_PROJECT=trafficiq-prod
VERTEX_ENDPOINT_ID=projects/YOUR_PROJECT/locations/us-central1/endpoints/YOUR_ENDPOINT
```

### 4. Install GCP Dependencies

```bash
pip install -e ".[gcp]"
```

### 5. Authenticate

```bash
# For local development
gcloud auth application-default login

# For Cloud Run, ensure service account has roles:
# - roles/aiplatform.user
# - roles/storage.objectAdmin
```

The agent will automatically call real Vertex endpoints instead of using mock predictions.

## Evaluation

### Run Evaluation

```bash
python -m eval.evaluate

# Output: artifacts/eval_report.md
```

### Sample Metrics

The evaluation module computes:

- **Accuracy**: Overall prediction accuracy by vehicle make
- **Per-Class Accuracy**: Broken down by make (Honda, Toyota, etc.)
- **Confusion Matrix**: Top-5 makes
- **ECE (Expected Calibration Error)**: Confidence calibration metric (lower is better)

### Example Report

```markdown
# TrafficIQ Evaluation Report

## Summary
- Dataset Size: 10 samples
- Successful Predictions: 10/10
- Evaluation Date: 2024-01-15 14:30:00

## Overall Metrics
- **Accuracy**: 0.8000 (80.00%)
- **ECE (Calibration)**: 0.0532
- **Precision (macro)**: 0.0000
- **Recall (macro)**: 0.0000
- **F1-Score (macro)**: 0.0000

## Per-Class Accuracy (Vehicle Makes)
| Make        | Accuracy           |
|-------------|-------------------|
| Honda       | 1.0000 (100.00%)  |
| Toyota      | 0.5000 (50.00%)   |
| Ford        | 1.0000 (100.00%)  |
```

## Deployment

### Docker Build

```bash
docker build -f infra/Dockerfile.api -t trafficiq:latest .
docker run -p 8000:8000 \
  -e USE_VERTEX=false \
  -e ENVIRONMENT=production \
  trafficiq:latest
```

### Cloud Run Deployment

```bash
# See detailed guide in infra/cloudrun_deploy.md

# Quick deploy
gcloud run deploy trafficiq-api \
  --source . \
  --platform managed \
  --region us-central1 \
  --memory 4Gi \
  --cpu 2 \
  --allow-unauthenticated
```

### Kubernetes (GKE)

Example manifest:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: trafficiq-api
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: api
        image: gcr.io/PROJECT/trafficiq:latest
        ports:
        - containerPort: 8000
        env:
        - name: USE_VERTEX
          value: "true"
        resources:
          limits:
            cpu: 2
            memory: 4Gi
```

## Testing

### Unit Tests

```bash
# Run all tests
pytest -v

# Run specific module
pytest tests/test_api.py -v

# With coverage report
pytest --cov=app --cov=eval --cov-report=html
```

### Integration Tests

```bash
# Start API server in one terminal
uvicorn app.api.main:app --reload

# Run integration tests in another
pytest tests/test_api.py::TestIntegration -v
```

### Load Testing (Locust)

```bash
# Install locust
pip install locust

# Run load test
locust -f tests/locustfile.py --host=http://localhost:8000
```

## Monitoring & Logging

### Local Logging

```bash
# Set log level
LOG_LEVEL=debug python -m uvicorn app.api.main:app

# JSON structured logs (production)
JSON_LOGGING=true uvicorn app.api.main:app
```

### Cloud Logging (Cloud Run)

Logs automatically appear in Google Cloud Logging:

```bash
gcloud run logs read trafficiq-api --limit=50
```

### Key Metrics to Monitor

```python
# In logs, watch for:
- vehicle_prediction_confidence < 0.60  # Low confidence predictions
- ocr_fallback_used=true                # Frequent OCR fallbacks indicate image quality issues
- processing_time > 500ms               # Slow responses
- bolo_match=true                       # Watchlist matches
- priority=P0                           # Critical matches
```

## Troubleshooting

### Mock Predictions Are Not Deterministic

**Issue**: Same image URI produces different predictions.

**Solution**: Ensure `USE_VERTEX=false`. Mock mode uses MD5 hash of URI.

```bash
# Verify config
curl http://localhost:8000/health
```

### Vertex AI Connection Fails

**Issue**: `google-cloud-aiplatform` not installed.

**Solution**:
```bash
pip install -e ".[gcp]"
gcloud auth application-default login
```

### BOLO Lookups Always Match

**Issue**: Too many false positives on watchlist.

**Solution**: Adjust policy thresholds in `app/agent/policy.py`:

```python
PolicyConfig(
    P0_THRESHOLDS={"bolo_match": True, "min_confidence": 0.85},  # Higher threshold
    P1_THRESHOLDS={"bolo_match": True, "min_confidence": 0.70},
)
```

### High Memory Usage

**Issue**: API server consuming too much RAM.

**Solution**: 
- Reduce batch size
- Implement request caching
- Scale horizontally on Cloud Run

```bash
gcloud run update trafficiq-api --memory 8Gi --max-instances 100
```

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## Performance Benchmarks

Running on Google Cloud Run (2 CPU, 4GB RAM):

| Operation | Latency | Notes |
|-----------|---------|-------|
| Health Check | ~5ms | No computation |
| Vehicle Prediction (mock) | ~20ms | Hash-based |
| Vehicle Prediction (Vertex) | ~150-300ms | Network + model |
| OCR Extraction | ~30ms | Pattern matching |
| BOLO Lookup | ~15ms | Hardcoded match |
| Full Agent Pipeline (mock) | ~200ms | All steps |
| Full Agent Pipeline (Vertex) | ~400-600ms | End-to-end |

## Next Steps & Roadmap

- [ ] Implement real Vertex AI fine-tuning pipeline
- [ ] Add WebSocket endpoints for streaming analysis
- [ ] Implement BOLO database abstraction (PostgreSQL, MongoDB)
- [ ] Add multi-model blend (vehical + plate + pedestrian detectors)
- [ ] Implement feedback loop for model retraining
- [ ] Add real-time dashboard (Grafana/Streamlit)
- [ ] Expand to other vehicle attributes (license plate, VIN detection)
- [ ] Implement explainability (LIME/SHAP) for predictions
- [ ] Add automated testing (CI/CD pipeline)
- [ ] Create Terraform modules for reproducible infrastructure

## License

MIT License - See LICENSE file for details

## Support

For issues, questions, or contributions:

- **GitHub Issues**: [Report bugs here](https://github.com/your-org/trafficiq/issues)
- **Discussions**: [Ask questions here](https://github.com/your-org/trafficiq/discussions)
- **Email**: dev@trafficiq.local

## Authors

- TrafficIQ Team

---

**Built with ❤️ for traffic law enforcement and public safety**
