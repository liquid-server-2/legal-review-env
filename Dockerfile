FROM python:3.11-slim

# HF Spaces convention: port 7860
ENV PORT=7860
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY *.py .
COPY openenv.yaml .

# Expose port
EXPOSE 7860

# Start the FastAPI server
CMD ["python", "server.py"]
