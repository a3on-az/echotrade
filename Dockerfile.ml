FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install ML-specific packages
RUN pip install scikit-learn pandas beautifulsoup4 selenium tweepy

# Copy application files
COPY . .

# Create data directory
RUN mkdir -p data

EXPOSE 8051

CMD ["python", "ml_model.py"]