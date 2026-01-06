FROM python:3.11-slim
ENV PIP_DEFAULT_TIMEOUT=1000

WORKDIR /app

# Copy requirements from project root (context is set to project root in compose.yml)
# UI Dockerfile
COPY apps/ui/requirements-ui.txt .
RUN pip install --no-cache-dir -r requirements-ui.txt

# Copy UI code
COPY apps/ui /app

# Copy data into container image
COPY data /app/data

EXPOSE 8501

#CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]
CMD ["python", "-m", "streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]
