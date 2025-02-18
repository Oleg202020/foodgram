FROM python:3.9

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt --default-timeout=100

COPY . .

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "foodgram_main.wsgi"]