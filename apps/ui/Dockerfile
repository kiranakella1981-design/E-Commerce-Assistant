FROM python:3.11-slim

ENV PIP_DEFAULT_TIMEOUT=1000 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (better cache)
COPY apps/ui/requirements-ui.txt .
RUN pip install --no-cache-dir -r requirements-ui.txt

# Copy UI code only
COPY apps/ui /app

# OPTIONAL: remove if UI doesn't need data
# COPY data /app/data

EXPOSE 8501

CMD ["python", "-m", "streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]
