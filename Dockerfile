FROM python:3.12-slim

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    HOME=/tmp \
    HF_HOME=/tmp/hf-home \
    TORCH_HOME=/tmp/torch-home \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY capabilities ./capabilities
RUN uv sync --frozen --no-dev --extra mcp-server --extra modern-encoder --extra reference-encoder

ENV MINDRIAN_EUREKA_RS_MODEL_PATH=/models/model \
    MINDRIAN_EUREKA_DATA_DIR=/data \
    MINDRIAN_EUREKA_RS_ENCODER=sentence-transformers
ENTRYPOINT ["uv", "run", "--no-sync", "eureka-mcp"]
