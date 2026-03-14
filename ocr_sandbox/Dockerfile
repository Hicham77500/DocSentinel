FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends tesseract-ocr poppler-utils && \
    rm -rf /var/lib/apt/lists/*

RUN groupadd --system sandbox && useradd --system --gid sandbox sandbox

WORKDIR /sandbox

COPY requirements.txt /sandbox/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /sandbox/requirements.txt

COPY app.py /sandbox/app.py

USER sandbox

EXPOSE 8080

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
