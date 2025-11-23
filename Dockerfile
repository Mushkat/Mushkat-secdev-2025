ARG PYTHON_VERSION=3.12.3

FROM python:${PYTHON_VERSION}-slim AS deps
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VENV_PATH=/opt/venv
WORKDIR /app
# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get install --no-install-recommends -y build-essential \
    && rm -rf /var/lib/apt/lists/*
RUN python -m venv ${VENV_PATH}
ENV PATH="${VENV_PATH}/bin:${PATH}"
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --upgrade "pip==${PYTHON_PIP_VERSION}" \
    && python -m pip install --no-cache-dir -r requirements.txt

FROM deps AS tester
COPY requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY app ./app
COPY tests ./tests
COPY docs ./docs
COPY README.md pyproject.toml ./
ENV PYTHONPATH=/app
RUN pytest -q

FROM python:${PYTHON_VERSION}-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}" \
    PYTHONPATH=/app \
    HEALTHCHECK_URL=http://127.0.0.1:8000/health \
    HEALTHCHECK_TIMEOUT=3 \
    DATABASE_URL=sqlite:////data/parking.db
WORKDIR /app
COPY --from=deps /opt/venv /opt/venv
RUN groupadd --system app \
    && useradd --system --gid app --create-home app \
    && install -d -o app -g app /data
COPY --chown=app:app app ./app
COPY --chown=app:app scripts ./scripts
VOLUME ["/data"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD ["python", "scripts/healthcheck.py"]
USER app
ENTRYPOINT ["uvicorn"]
CMD ["app.main:app", "--host", "0.0.0.0", "--port", "8000"]
