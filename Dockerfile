FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py config.py ./
COPY templates ./templates
COPY static ./static
RUN mkdir -p /app/data
ENV DATABASE_PATH=/app/data/rsvps.sqlite3
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "4", "app:app"]
