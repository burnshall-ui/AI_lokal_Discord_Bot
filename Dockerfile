FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all Python files
COPY *.py .

# Create data directories
RUN mkdir -p /app/data /app/logs

CMD ["python", "-u", "bot.py"]
