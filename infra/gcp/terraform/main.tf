provider "google" {
  project = var.project_id
  region  = var.region
}

# -----------------------
# Service Accounts
# -----------------------
resource "google_service_account" "api" {
  account_id   = "hakilix-api"
  display_name = "Hakilix API"
}

resource "google_service_account" "worker" {
  account_id   = "hakilix-worker"
  display_name = "Hakilix Worker"
}

resource "google_service_account" "migrator" {
  account_id   = "hakilix-migrator"
  display_name = "Hakilix Migrator"
}

resource "google_service_account" "pubsub_pusher" {
  account_id   = "hakilix-pubsub-pusher"
  display_name = "Hakilix Pub/Sub OIDC Pusher Identity"
}

# -----------------------
# Cloud SQL (PostgreSQL)
# -----------------------
resource "google_sql_database_instance" "pg" {
  name             = var.db_instance_name
  database_version = var.db_version
  region           = var.region
  deletion_protection = var.db_deletion_protection

  settings {
    tier = var.db_tier

    disk_type = "PD_SSD"
    disk_size = var.db_disk_gb

    availability_type = var.db_high_availability ? "REGIONAL" : "ZONAL"

    ip_configuration {
      ipv4_enabled = var.db_public_ip
      # For production: prefer private IP + Serverless VPC Access.
    }

    backup_configuration {
      enabled = true
    }
  }
}

resource "google_sql_database" "hakilix" {
  name     = var.db_name
  instance = google_sql_database_instance.pg.name
}

resource "random_password" "db_admin" {
  length  = 24
  special = true
}

resource "random_password" "db_app" {
  length  = 24
  special = true
}

resource "random_password" "db_ingest" {
  length  = 24
  special = true
}

resource "google_sql_user" "admin" {
  name     = "hakilix_migrator"
  instance = google_sql_database_instance.pg.name
  password = random_password.db_admin.result
}

resource "google_sql_user" "app" {
  name     = "hakilix_app"
  instance = google_sql_database_instance.pg.name
  password = random_password.db_app.result
}

resource "google_sql_user" "ingest" {
  name     = "hakilix_ingest"
  instance = google_sql_database_instance.pg.name
  password = random_password.db_ingest.result
}

locals {
  cloudsql_conn = google_sql_database_instance.pg.connection_name
  # SQLAlchemy URL using Cloud SQL unix socket mounted into Cloud Run at /cloudsql/<connection_name>
  db_url_admin  = "postgresql+psycopg://${google_sql_user.admin.name}:${random_password.db_admin.result}@/${google_sql_database.hakilix.name}?host=/cloudsql/${local.cloudsql_conn}"
  db_url_app    = "postgresql+psycopg://${google_sql_user.app.name}:${random_password.db_app.result}@/${google_sql_database.hakilix.name}?host=/cloudsql/${local.cloudsql_conn}"
  db_url_ingest = "postgresql+psycopg://${google_sql_user.ingest.name}:${random_password.db_ingest.result}@/${google_sql_database.hakilix.name}?host=/cloudsql/${local.cloudsql_conn}"
}

# -----------------------
# Secret Manager
# -----------------------
resource "google_secret_manager_secret" "jwt" {
  secret_id = "hakilix-jwt-secret"
  replication { auto {} }
}
resource "google_secret_manager_secret_version" "jwt_v1" {
  secret      = google_secret_manager_secret.jwt.id
  secret_data = var.hakilix_jwt_secret
}

resource "google_secret_manager_secret" "db_admin" {
  secret_id = "hakilix-database-url-migrator"
  replication { auto {} }
}
resource "google_secret_manager_secret_version" "db_admin_v1" {
  secret      = google_secret_manager_secret.db_admin.id
  secret_data = local.db_url_admin
}

resource "google_secret_manager_secret" "db_app" {
  secret_id = "hakilix-database-url-app"
  replication { auto {} }
}
resource "google_secret_manager_secret_version" "db_app_v1" {
  secret      = google_secret_manager_secret.db_app.id
  secret_data = local.db_url_app
}

resource "google_secret_manager_secret" "db_ingest" {
  secret_id = "hakilix-database-url-ingest"
  replication { auto {} }
}
resource "google_secret_manager_secret_version" "db_ingest_v1" {
  secret      = google_secret_manager_secret.db_ingest.id
  secret_data = local.db_url_ingest
}

# Allow Cloud Run SAs to access required secrets
resource "google_secret_manager_secret_iam_member" "api_secret_access_jwt" {
  secret_id = google_secret_manager_secret.jwt.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api.email}"
}
resource "google_secret_manager_secret_iam_member" "api_secret_access_db" {
  secret_id = google_secret_manager_secret.db_app.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api.email}"
}
resource "google_secret_manager_secret_iam_member" "worker_secret_access_db" {
  secret_id = google_secret_manager_secret.db_ingest.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.worker.email}"
}
resource "google_secret_manager_secret_iam_member" "migrator_secret_access_db" {
  secret_id = google_secret_manager_secret.db_admin.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.migrator.email}"
}
resource "google_secret_manager_secret_iam_member" "worker_secret_access_jwt" {
  secret_id = google_secret_manager_secret.jwt.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.worker.email}"
}

# -----------------------
# Pub/Sub broker
# -----------------------
resource "google_pubsub_topic" "telemetry" {
  name = "hakilix-telemetry"
}

resource "google_pubsub_subscription" "telemetry_push" {
  name  = "hakilix-telemetry-push"
  topic = google_pubsub_topic.telemetry.name

  push_config {
    push_endpoint = "${google_cloud_run_v2_service.worker.uri}/v1/pubsub/push"

    oidc_token {
      service_account_email = google_service_account.pubsub_pusher.email
      audience              = google_cloud_run_v2_service.worker.uri
    }
  }
}

# -----------------------
# IAM: Cloud SQL Client
# -----------------------
resource "google_project_iam_member" "api_cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.api.email}"
}

resource "google_project_iam_member" "worker_cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.worker.email}"
}

resource "google_project_iam_member" "migrator_cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.migrator.email}"
}

# -----------------------
# Cloud Run: API
# -----------------------
resource "google_cloud_run_v2_service" "api" {
  name     = "hakilix-api"
  location = var.region

  template {
    service_account = google_service_account.api.email

    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [local.cloudsql_conn]
      }
    }

    containers {
      image = var.api_image

      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }

      env { name = "HAKILIX_ENV" value = "prod" }

      env { name = "DATABASE_URL_APP" value = "sm://projects/${var.project_id}/secrets/${google_secret_manager_secret.db_app.secret_id}/versions/latest" }
      env { name = "DATABASE_URL_MIGRATOR" value = "sm://projects/${var.project_id}/secrets/${google_secret_manager_secret.db_admin.secret_id}/versions/latest" }
      env { name = "HAKILIX_JWT_SECRET" value = "sm://projects/${var.project_id}/secrets/${google_secret_manager_secret.jwt.secret_id}/versions/latest" }

      env { name = "BROKER_TYPE" value = "pubsub" }
      env { name = "PUBSUB_TOPIC" value = "projects/${var.project_id}/topics/${google_pubsub_topic.telemetry.name}" }

      env { name = "OIDC_ENABLED" value = tostring(var.oidc_enabled) }
      env { name = "OIDC_ISSUER" value = var.oidc_issuer }
      env { name = "OIDC_AUDIENCE" value = var.oidc_audience }
      env { name = "OIDC_JWKS_URL" value = var.oidc_jwks_url }

      env { name = "OTEL_ENABLED" value = "true" }
    }
  }
}

# -----------------------
# Cloud Run: Worker (Pub/Sub push endpoint)
# -----------------------
resource "google_cloud_run_v2_service" "worker" {
  name     = "hakilix-worker"
  location = var.region

  template {
    service_account = google_service_account.worker.email

    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [local.cloudsql_conn]
      }
    }

    containers {
      image = var.worker_image

      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }

      env { name = "DATABASE_URL_INGEST" value = "sm://projects/${var.project_id}/secrets/${google_secret_manager_secret.db_ingest.secret_id}/versions/latest" }
      env { name = "REDIS_URL" value = "redis://<memorystore-host>:6379/0" } # Replace with Memorystore
      env { name = "HAKILIX_JWT_SECRET" value = "sm://projects/${var.project_id}/secrets/${google_secret_manager_secret.jwt.secret_id}/versions/latest" }
      env { name = "OTEL_ENABLED" value = "true" }
    }
  }
}

# -----------------------
# Cloud Run: Migrator job (run alembic + seed)
# -----------------------
resource "google_cloud_run_v2_job" "migrate" {
  name     = "hakilix-migrate"
  location = var.region

  template {
    template {
      service_account = google_service_account.migrator.email

      volumes {
        name = "cloudsql"
        cloud_sql_instance { instances = [local.cloudsql_conn] }
      }

      containers {
        image = var.migrate_image

        volume_mounts {
          name       = "cloudsql"
          mount_path = "/cloudsql"
        }

        env { name = "DATABASE_URL_MIGRATOR" value = "sm://projects/${var.project_id}/secrets/${google_secret_manager_secret.db_admin.secret_id}/versions/latest" }
        env { name = "DATABASE_URL_APP" value = "sm://projects/${var.project_id}/secrets/${google_secret_manager_secret.db_app.secret_id}/versions/latest" }
        env { name = "HAKILIX_JWT_SECRET" value = "sm://projects/${var.project_id}/secrets/${google_secret_manager_secret.jwt.secret_id}/versions/latest" }
        env { name = "SEED_DEMO" value = "true" }
      }
    }
  }
}

# -----------------------
# Cloud Run: Dashboard
# -----------------------
resource "google_cloud_run_v2_service" "dashboard" {
  name     = "hakilix-dashboard"
  location = var.region
  template {
    containers {
      image = var.dashboard_image
      env { name = "API_BASE_URL" value = google_cloud_run_v2_service.api.uri }
    }
  }
}

output "api_url" { value = google_cloud_run_v2_service.api.uri }
output "dashboard_url" { value = google_cloud_run_v2_service.dashboard.uri }
output "pubsub_topic" { value = google_pubsub_topic.telemetry.name }
output "cloudsql_connection_name" { value = local.cloudsql_conn }
