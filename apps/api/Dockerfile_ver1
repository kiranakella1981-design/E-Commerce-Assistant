FROM python:3.11-slim
ENV PIP_DEFAULT_TIMEOUT=1000

WORKDIR /app

# API Dockerfile
COPY apps/api/requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt
RUN pip install torch==2.5.1 -f https://download.pytorch.org/whl/torch_stable.html

# Copy API code
COPY apps/api /app

# Copy data into container image
COPY data /app/data

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
