FROM python:3.12-slim

# Install Playwright system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 \
    libgbm1 libpango-1.0-0 libcairo2 libasound2t64 \
    libxdamage1 libxrandr2 libxcomposite1 libxfixes3 \
    libcups2 libatspi2.0-0 libx11-xcb1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install chromium

COPY . .

VOLUME ["/app/data", "/app/browser_data"]

CMD ["python", "-m", "src.main"]
