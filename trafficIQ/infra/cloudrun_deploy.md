# Cloud Run Deployment Guide for TrafficIQ

## Prerequisites

- GCP Project with Cloud Run enabled
- `gcloud` CLI installed and authenticated
- Docker installed locally
- Vertex AI endpoint created (optional, for real predictions)

## Architecture

TrafficIQ is deployed as containerized microservices on Cloud Run:

- **API Service**: FastAPI backend for /analyze and /agent/run endpoints
- **Agent Service**: Batch processing service for evaluation runs
- **Shared Storage**: GCS buckets for artifacts and evidence packets

## Environment Setup

### 1. Create GCS Bucket for Artifacts

```bash
PROJECT_ID=your-gcp-project
BUCKET_NAME=trafficiq-artifacts-${PROJECT_ID}

gsutil mb gs://${BUCKET_NAME}/
```

### 2. Set Environment Variables

Create a `.env` file for Cloud Run:

```bash
# GCP Configuration
GCP_PROJECT=${PROJECT_ID}
GCP_REGION=us-central1
VERTEX_ENDPOINT_ID=projects/${PROJECT_ID}/locations/us-central1/endpoints/your-endpoint-id

# Service Configuration
ENVIRONMENT=production
USE_VERTEX=true
USE_GCS=true
GCS_BUCKET=${BUCKET_NAME}

# Security
JSON_LOGGING=true
DEBUG=false
```

## Deployment

### 1. Build Docker Image

```bash
docker build -f infra/Dockerfile.api -t trafficiq-api:latest .
```

### 2. Push to Google Container Registry

```bash
# Configure Docker auth
gcloud auth configure-docker gcr.io

# Tag image
docker tag trafficiq-api:latest gcr.io/${PROJECT_ID}/trafficiq-api:latest

# Push image
docker push gcr.io/${PROJECT_ID}/trafficiq-api:latest
```

### 3. Deploy to Cloud Run

```bash
gcloud run deploy trafficiq-api \
  --image gcr.io/${PROJECT_ID}/trafficiq-api:latest \
  --platform managed \
  --region us-central1 \
  --memory 4Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 100 \
  --set-env-vars GCP_PROJECT=${PROJECT_ID},USE_VERTEX=true,GCS_BUCKET=${BUCKET_NAME} \
  --allow-unauthenticated
```

### 4. Set Secrets (Optional)

For sensitive configuration:

```bash
# Create secret
echo -n "your-api-key" | gcloud secrets create trafficiq-api-key --data-file=-

# Use in Cloud Run
gcloud run deploy trafficiq-api \
  --update-secrets VERTEX_API_KEY=trafficiq-api-key:latest \
  ...
```

## API Endpoints

After deployment, your API will be available at:

```
https://trafficiq-api-${RANDOM_ID}.a.run.app
```

### Health Check

```bash
curl https://trafficiq-api-${RANDOM_ID}.a.run.app/health
```

### Analyze Vehicle

```bash
curl -X POST https://trafficiq-api-${RANDOM_ID}.a.run.app/analyze \
  -H "Content-Type: application/json" \
  -d '{"image_uri": "gs://your-bucket/image.jpg"}'
```

### Run Full Agent Pipeline

```bash
curl -X POST https://trafficiq-api-${RANDOM_ID}.a.run.app/agent/run \
  -H "Content-Type: application/json" \
  -d '{
    "image_uri": "gs://your-bucket/image.jpg",
    "location": "Downtown Intersection A",
    "timestamp": "2024-01-15T14:30:00Z"
  }'
```

## Monitoring

### View Logs

```bash
gcloud run logs read trafficiq-api --limit 50
```

### View Metrics

```bash
gcloud monitoring dashboards list
gcloud monitoring metrics-descriptors list
```

### Set Up Alerting

```bash
# High error rate alert
gcloud alpha monitoring policies create \
  --notification-channels=YOUR_CHANNEL_ID \
  --display-name="TrafficIQ High Error Rate" \
  --condition-display-name="Error rate > 5%" \
  ...
```

## Auto-Scaling

Cloud Run automatically scales based on traffic. Configure limits:

```bash
gcloud run update trafficiq-api \
  --min-instances 1 \
  --max-instances 100
```

## Database/Storage

For persistent case data, mount Cloud Storage as FUSE:

```bash
gcloud run deploy trafficiq-api \
  --image gcr.io/${PROJECT_ID}/trafficiq-api:latest \
  --volumes /artifacts=gs://${BUCKET_NAME}/artifacts \
  ...
```

Or use Cloud SQL for structured data:

```python
# In app/tools/case_client.py, add Cloud SQL connector
from cloud.sql.connector import Connector

connector = Connector()
conn = connector.connect(
    "project:region:instance",
    "postgresql",
    user="postgres",
    password="password",
    db="trafficiq",
)
```

## Cost Optimization

1. **Use memory/CPU wisely**: Start with 2GB/1CPU, scale as needed
2. **Set max-instances** to prevent runaway costs
3. **Use Cloud CDN** for artifact caching
4. **Archive old cases** to long-term storage (GCS Nearline)

## Continuous Deployment (CI/CD)

### Cloud Build Integration

```yaml
# cloudbuild.yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/trafficiq-api:$COMMIT_SHA', '.']
  
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/trafficiq-api:$COMMIT_SHA']
  
  - name: 'gcr.io/cloud-builders/gke-deploy'
    args: ['run', '--filename=k8s/', '--image=gcr.io/$PROJECT_ID/trafficiq-api:$COMMIT_SHA', '--location=us-central1', '--cluster=trafficiq']
```

## Troubleshooting

### API not responding

```bash
# Check Cloud Run status
gcloud run services describe trafficiq-api --region us-central1

# View recent logs
gcloud run logs read trafficiq-api --limit 100 --region us-central1
```

### High latency

- Check Vertex AI endpoint availability
- Review concurrent request limits
- Monitor Cold start times (default ~5s after idle)

### Authentication errors

```bash
# Verify service account has required roles
gcloud iam service-accounts get-iam-policy \
  trafficiq-api@${PROJECT_ID}.iam.gserviceaccount.com
```

## Rollback

```bash
# List revisions
gcloud run revisions list --service trafficiq-api

# Deploy previous version
gcloud run deploy trafficiq-api \
  --image gcr.io/${PROJECT_ID}/trafficiq-api:previous-tag
```
