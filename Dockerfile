FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip uninstall --yes pip

COPY src ./src

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/input /app/output \
    && chown -R appuser:appuser /app

USER 10001

ENTRYPOINT ["python", "-m", "src.podcast_agent.main"]