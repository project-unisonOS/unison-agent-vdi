FROM ghcr.io/project-unisonos/unison-common-wheel:latest AS common_wheel
FROM python:3.12-slim@sha256:fdab368dc2e04fab3180d04508b41732756cc442586f708021560ee1341f3d29

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl git ca-certificates \
    libnss3 libatk-bridge2.0-0 libgtk-3-0 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libgbm1 libasound2 libpangocairo-1.0-0 libpango-1.0-0 \
    libcairo2 fonts-liberation fonts-unifont wget \
    && rm -rf /var/lib/apt/lists/*

COPY constraints.txt ./constraints.txt
COPY requirements.txt ./requirements.txt
COPY --from=common_wheel /tmp/wheels /tmp/wheels
RUN pip install --no-cache-dir -c ./constraints.txt /tmp/wheels/unison_common-*.whl \
    && pip install --no-cache-dir -c ./constraints.txt -r requirements.txt \
    && python -m playwright install chromium

COPY src ./src
COPY tests ./tests

ENV PYTHONPATH=/app/src
EXPOSE 8083
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8083"]
