FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install
COPY frontend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY frontend /app/frontend

EXPOSE 8501

CMD ["streamlit", "run", "frontend/app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
