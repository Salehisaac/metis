# Fixed: pinned slim base, no baked-in secret, non-root user, exec-form CMD.
FROM python:3.12.16-slim
WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt
RUN groupadd -r appuser && useradd --no-log-init -r -g appuser appuser
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
