FROM python:3.11-slim

ARG SPACY_MODEL_WHL="https://github.com/explosion/spacy-models/releases/download/es_core_news_md-3.7.0/es_core_news_md-3.7.0-py3-none-any.whl"

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/workspace

WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt

RUN python -m pip install --upgrade pip setuptools wheel && \
    python -m pip install -r /tmp/requirements.txt && \
    python -m pip install "${SPACY_MODEL_WHL}"

COPY . /workspace

RUN test -f /workspace/Spanish_Psych_Phenotyping_PY/escribe/default_nlp.py || \
    (echo "Submódulo Spanish_Psych_Phenotyping_PY no inicializado." && exit 1)

CMD ["bash"]
