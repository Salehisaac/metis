# Works and passes last lesson's rules, but every code change reinstalls all dependencies,
# the build context drags in everything, and nothing tells Docker whether the app is healthy.
# The app serves GET /health on port 8000 (returns 200 when it's up).
FROM python:3.12.16-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
RUN groupadd -r appuser && useradd --no-log-init -r -g appuser appuser
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
