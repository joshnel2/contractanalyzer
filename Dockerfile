FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Azure App Service uses port 8000 by default
EXPOSE 8000

# Run with gunicorn - timeout increased for large dataset processing
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--timeout", "600", "--workers", "2", "app:app"]
