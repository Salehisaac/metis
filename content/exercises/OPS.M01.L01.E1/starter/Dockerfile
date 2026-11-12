# A colleague's Dockerfile for the FastAPI app in app/main.py (app = FastAPI()).
# It builds, but it breaks four rules from the lesson. Fix them; keep the app on port 8000.
FROM python:latest
ENV OAUTH_CLIENT_SECRET=s3cr3t-do-not-ship
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
EXPOSE 8000
CMD uvicorn app.main:app --host 0.0.0.0 --port 8000
