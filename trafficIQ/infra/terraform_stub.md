# Terraform Configuration for TrafficIQ Infrastructure

This is a stub for infrastructure as code (IaC) using Terraform. Complete the implementation based on your specific requirements.

## Directory Structure

```
terraform/
├── main.tf              # Main configuration
├── variables.tf         # Input variables
├── outputs.tf           # Output values
├── cloud_run.tf         # Cloud Run services
├── storage.tf           # GCS buckets
├── networking.tf        # VPC, IAM, etc.
└── terraform.tfvars     # Variable values (not checked in)
```

## Setup

### 1. Initialize Terraform

```bash
cd terraform
terraform init
```

### 2. Create terraform.tfvars

```hcl
project_id = "your-gcp-project"
region      = "us-central1"
environment = "production"
```

### 3. Plan Deployment

```bash
terraform plan
```

### 4. Apply Configuration

```bash
terraform apply
```

## Example Configuration

### main.tf

```hcl
terraform {
  required_version = ">= 1.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  
  backend "gcs" {
    bucket = "trafficiq-terraform-state"
    prefix = "prod"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
```

### variables.tf

```hcl
variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be dev, staging, or production."
  }
}
```

### cloud_run.tf

```hcl
# Create service account
resource "google_service_account" "trafficiq" {
  account_id   = "trafficiq-api"
  display_name = "TrafficIQ API Service Account"
}

# Cloud Run service
resource "google_cloud_run_service" "api" {
  name     = "trafficiq-api"
  location = var.region

  template {
    spec {
      service_account_name = google_service_account.trafficiq.email

      containers {
        image = "gcr.io/${var.project_id}/trafficiq-api:latest"

        env {
          name  = "ENVIRONMENT"
          value = var.environment
        }
        
        env {
          name  = "USE_VERTEX"
          value = "true"
        }
        
        env {
          name  = "GCS_BUCKET"
          value = google_storage_bucket.artifacts.name
        }

        resources {
          limits = {
            cpu    = "2"
            memory = "4Gi"
          }
        }
      }

      timeout_seconds = 300
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/maxScale" = "100"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [
    google_project_iam_member.trafficiq_gcs,
    google_project_iam_member.trafficiq_vertex,
  ]
}

# Allow unauthenticated access
resource "google_cloud_run_service_iam_member" "public" {
  service  = google_cloud_run_service.api.name
  location = google_cloud_run_service.api.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}
```

### storage.tf

```hcl
# GCS bucket for artifacts
resource "google_storage_bucket" "artifacts" {
  name          = "trafficiq-artifacts-${var.project_id}"
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 90  # days
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }
}

# GCS bucket for Terraform state
resource "google_storage_bucket" "terraform_state" {
  name     = "trafficiq-terraform-state"
  location = var.region

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }
}
```

## Outputs

### outputs.tf

```hcl
output "api_endpoint" {
  value       = google_cloud_run_service.api.status[0].url
  description = "Cloud Run API endpoint"
}

output "artifacts_bucket" {
  value       = google_storage_bucket.artifacts.name
  description = "Artifacts storage bucket"
}
```

## Commands

```bash
# Format code
terraform fmt -recursive

# Validate configuration
terraform validate

# Show plan
terraform plan -out=tfplan

# Apply configuration
terraform apply tfplan

# Destroy resources
terraform destroy
```

## State Management

### Remote State (Recommended)

```bash
# Create state bucket
gsutil mb gs://trafficiq-terraform-state/

# Configure backend in main.tf (see above)
terraform init
```

### State Lock

Terraform will automatically lock state during operations. For manual unlock:

```bash
terraform force-unlock LOCK_ID
```

## Best Practices

1. **Always use `terraform plan` before apply**
2. **Store tfvars in secret management (e.g., Google Cloud Secret Manager)**
3. **Use workspaces for multiple environments**
4. **Enable audit logging for infrastructure changes**
5. **Use modules for reusable infrastructure components**

## Workspace Example

```bash
# Create workspaces
terraform workspace new staging
terraform workspace new production

# Select workspace
terraform workspace select production

# Plan for specific workspace
terraform plan -var-file="staging.tfvars"
```
