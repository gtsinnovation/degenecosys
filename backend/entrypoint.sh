#!/bin/sh

echo "Launching Degen Ecosystem database connectivity check..."

# Active loop using Python to verify when the DB container opens its network port
python -c "
import socket, time
s = socket.socket()
while True:
    try:
        s.connect(('db', 5432))
        print('PostgreSQL container port 5432 is open and listening!')
        break
    except Exception:
        print('Waiting for database container network to initialize...')
        time.sleep(1)
"

echo "Syncing schema definitions..."
prisma db push --schema=./app/schema.prisma

echo "Starting FastAPI Core Engine application server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000