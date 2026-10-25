FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY relay.py app.html .
ENV PORT=8080
CMD ["sh", "-c", "uvicorn relay:app --host 0.0.0.0 --port ${PORT}"]
