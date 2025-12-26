# Security hardening (Cloud Run)

## OIDC (Clinician / Agency portal)
Hakilix API supports verifying OIDC JWTs (RS256) using a JWKS endpoint:
- `OIDC_ENABLED=true`
- `OIDC_ISSUER=...`
- `OIDC_AUDIENCE=hakilix-api`
- `OIDC_JWKS_URL=https://.../.well-known/jwks.json`

In production, prefer an IdP you already operate (e.g., Keycloak / Microsoft Entra ID). You can also protect the Streamlit dashboard with Cloud Run IAM or IAP and remove application-level login entirely.

## mTLS (Edge -> API)
Cloud Run does not natively enforce mutual TLS at the container boundary. For mTLS:
1. Place `hakilix-api` behind an external HTTPS Load Balancer.
2. Configure mTLS on the load balancer (trust config + client certificate verification).
3. Restrict direct Cloud Run access (ingress internal or only from the load balancer).

## Secrets
The code supports Secret Manager references using:
`sm://projects/<project>/secrets/<secret>/versions/<version|latest>`

Store:
- JWT signing secret
- DB URLs / credentials
- Any downstream keys (FHIR/NHS bridge, etc.)

Rotate secrets using Secret Manager versions and rollout via Cloud Run revisions.

## RLS + least privilege
The database uses Row Level Security (RLS) keyed on `current_setting('app.tenant_id', true)`.
Create distinct DB users:
- `hakilix_app`: API read/write within tenant
- `hakilix_ingest`: ingest-only
- `hakilix_readonly`: analytics/read-only
