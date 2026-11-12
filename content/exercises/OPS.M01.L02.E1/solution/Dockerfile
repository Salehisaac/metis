FROM python:3.12.16-slim
WORKDIR /app
RUN groupadd -r appuser && useradd --no-log-init -r -g appuser appuser
# Dependencies first: this layer is reused until requirements.txt changes.
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt
# Source last: it changes on every commit.
COPY app/ /app/app/
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
