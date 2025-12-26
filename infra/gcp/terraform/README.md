# Hakilix on GCP (Cloud Run + Cloud SQL Postgres)

This Terraform package deploys:
- Cloud SQL for PostgreSQL (instance + database + users)
- Cloud Run services:
  - `hakilix-api`
  - `hakilix-worker` (Pub/Sub push endpoint)
  - `hakilix-dashboard`
- Cloud Run Job:
  - `hakilix-migrate` (runs Alembic migrations + demo seed)
- Pub/Sub topic + push subscription for telemetry ingestion
- Secret Manager secrets for DB URLs and JWT secret

## Prereqs
- Terraform >= 1.5
- GCP project with billing enabled
- APIs enabled: Cloud Run, Cloud SQL Admin, Secret Manager, Pub/Sub, IAM

## Apply

1) Build/push container images and set:
- `api_image`
- `worker_image`
- `dashboard_image`
- `migrate_image`

2) Create `terraform.tfvars`:
```hcl
project_id = "YOUR_PROJECT"
region     = "europe-west2"

api_image       = "europe-west2-docker.pkg.dev/YOUR_PROJECT/hakilix/api:TAG"
worker_image    = "europe-west2-docker.pkg.dev/YOUR_PROJECT/hakilix/worker:TAG"
dashboard_image = "europe-west2-docker.pkg.dev/YOUR_PROJECT/hakilix/dashboard:TAG"
migrate_image   = "europe-west2-docker.pkg.dev/YOUR_PROJECT/hakilix/migrate:TAG"

hakilix_jwt_secret = "CHANGE_ME_LONG_RANDOM"

# Cloud SQL settings
db_instance_name      = "hakilix-pg"
db_name               = "hakilix"
db_tier               = "db-custom-2-8192"
db_disk_gb            = 50
db_high_availability  = false
db_deletion_protection = true
db_public_ip          = true

# Optional OIDC
oidc_enabled = false
```

3) Deploy:
```bash
terraform init
terraform apply
```

4) Run migrations (one-time, or on each release):
```bash
gcloud run jobs execute hakilix-migrate --region europe-west2 --wait
```

## Production recommendations
- Prefer Cloud SQL private IP + Serverless VPC Access, and restrict ingress to your API.
- Protect the dashboard using Cloud Run IAM or IAP.
- TimescaleDB is not available on Cloud SQL; Hakilix automatically falls back to standard PostgreSQL analytics views.
