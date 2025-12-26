FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends bash ca-certificates   && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY hakilix /app/hakilix
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini

EXPOSE 8080
CMD ["bash", "-lc", "python -m hakilix.app_entry"]
