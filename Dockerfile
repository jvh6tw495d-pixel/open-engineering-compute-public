# OEC API image (optional). Core library needs no container.
#   docker build -t oec:0.1.0 .
#   docker run --rm -p 8080:8080 oec:0.1.0

FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
COPY skills ./skills

RUN uv sync --frozen --extra api --no-dev \
    && uv pip install --system -e ".[api]"

ENV PYTHONUNBUFFERED=1
EXPOSE 8080

CMD ["oec", "server", "api", "--host", "0.0.0.0", "--port", "8080", "--skills-root", "skills"]
