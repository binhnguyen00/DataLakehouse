FROM apache/superset:6.1.0

USER root
RUN uv pip install --python /app/.venv/bin/python --no-cache trino==0.340.0

USER superset
