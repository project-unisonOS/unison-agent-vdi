FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY constraints.txt ./constraints.txt
COPY unison-common /app/unison-common
COPY unison-agent-vdi/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -c ./constraints.txt /app/unison-common \
    && pip install --no-cache-dir -c ./constraints.txt -r requirements.txt

COPY unison-agent-vdi/src ./src
COPY unison-agent-vdi/tests ./tests

ENV PYTHONPATH=/app/src
EXPOSE 8093
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8083"]
