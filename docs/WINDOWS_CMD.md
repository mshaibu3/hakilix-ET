# Windows CMD runbook
```bat
copy .env.example .env
docker compose up -d --build
docker compose logs -f hakilix-migrate
curl http://127.0.0.1:8080/v1/health
```
Dashboard: http://127.0.0.1:8501
DB host port: 55432 (change if needed).
