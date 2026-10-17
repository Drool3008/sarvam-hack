# Universal image: runs on Render, Hugging Face Spaces, Cloud Run or any host
# that sets $PORT. The Sarvam keys are injected as environment variables at run
# time and are never baked into the image.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend

# Hugging Face Spaces expects 7860; Render and Cloud Run inject $PORT.
ENV PORT=7860
EXPOSE 7860

# Writable scratch for rendered TTS audio.
RUN mkdir -p /srv/out && chmod 777 /srv/out

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860} --app-dir backend"]
