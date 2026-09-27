FROM python:3.11-slim

WORKDIR /workspace

# Install system dependencies needed for prebuilt Node binaries (libatomic1)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libatomic1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all backend files (app, scripts, database schemas, and entrypoint)
COPY . .

# Convert entrypoint line breaks to Linux standard formats and grant permissions
RUN sed -i 's/\r$//' entrypoint.sh && chmod +x entrypoint.sh

# Run Prisma schema tracking generation safely
RUN prisma generate --schema=./app/schema.prisma

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]