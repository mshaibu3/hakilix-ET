# Docker Hub publishing & consumption (mshaibu)

## Images

- `mshaibu/hakilix-api`
- `mshaibu/hakilix-worker`
- `mshaibu/hakilix-dashboard`
- `mshaibu/hakilix-inference`
- `mshaibu/hakilix-telemetry-sim`

`hakilix-migrate` uses the same image as `hakilix-api` and just runs a different command.

## Recommended tags

- Use semver tags for releases: `v1.0.0` (Git tag) → pushes image tag `v1.0.0`
- Keep `latest` for the default branch only

## Run locally using Docker Hub images (no build)

```bash
export TAG=latest
docker compose pull
docker compose up -d
```

## Publish manually (developer workstation)

```bash
docker login
export TAG=1.0.0

docker build -t mshaibu/hakilix-api:$TAG -f hakilix_enterprise_advanced/services/api/Dockerfile hakilix_enterprise_advanced/services/api
docker build -t mshaibu/hakilix-worker:$TAG -f hakilix_enterprise_advanced/services/worker/Dockerfile hakilix_enterprise_advanced/services/worker
docker build -t mshaibu/hakilix-dashboard:$TAG -f hakilix_enterprise_advanced/services/dashboard/Dockerfile hakilix_enterprise_advanced/services/dashboard
docker build -t mshaibu/hakilix-inference:$TAG -f hakilix_enterprise_advanced/services/inference/Dockerfile hakilix_enterprise_advanced/services/inference
docker build -t mshaibu/hakilix-telemetry-sim:$TAG -f hakilix_enterprise_advanced/services/telemetry_sim/Dockerfile hakilix_enterprise_advanced/services/telemetry_sim

docker push mshaibu/hakilix-api:$TAG
docker push mshaibu/hakilix-worker:$TAG
docker push mshaibu/hakilix-dashboard:$TAG
docker push mshaibu/hakilix-inference:$TAG
docker push mshaibu/hakilix-telemetry-sim:$TAG
```

## Publish via GitHub Actions

Workflow: `.github/workflows/publish-dockerhub.yml`

Secrets required:
- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

The workflow builds multi-arch images (`amd64`, `arm64`) and pushes tags for:
- default branch → `latest` and `sha-<short>`
- version tags (e.g. `v1.0.0`) → `v1.0.0`
