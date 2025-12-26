variable "project_id" { type = string }
variable "region" { type = string  default = "europe-west2" }

variable "api_image" { type = string }
variable "worker_image" { type = string }
variable "dashboard_image" { type = string }
variable "migrate_image" { type = string }

# Secrets (bootstrap only; rotate after first apply)
variable "hakilix_jwt_secret" { type = string  sensitive = true }

# Cloud SQL (PostgreSQL)
variable "db_instance_name" { type = string default = "hakilix-pg" }
variable "db_name" { type = string default = "hakilix" }
variable "db_version" { type = string default = "POSTGRES_14" }
variable "db_tier" { type = string default = "db-custom-2-8192" }
variable "db_disk_gb" { type = number default = 50 }
variable "db_high_availability" { type = bool default = false }
variable "db_deletion_protection" { type = bool default = true }
variable "db_public_ip" { type = bool default = true }

# Optional: OIDC (Keycloak/Entra etc) for clinician console / API
variable "oidc_enabled" { type = bool default = false }
variable "oidc_issuer" { type = string default = "" }
variable "oidc_audience" { type = string default = "hakilix-api" }
variable "oidc_jwks_url" { type = string default = "" }
