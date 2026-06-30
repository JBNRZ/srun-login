FROM python:3.12-alpine

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup -S app && adduser -S -G app app && chown app:app /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY --chown=app:app login.py ./login.py
COPY --chown=app:app utils ./utils

USER app

CMD ["python", "login.py"]
