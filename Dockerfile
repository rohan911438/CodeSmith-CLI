# CodeSmith CLI - container to run a specific agent with uvicorn
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (optional, keep minimal)
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Choose which agent to run at container start
ARG AGENT_NAME=apitest
ENV AGENT_NAME=${AGENT_NAME}
ENV PORT=8000

EXPOSE 8000

# Run the selected agent
CMD ["sh", "-c", "python -m uvicorn agents.${AGENT_NAME}.main:app --host 0.0.0.0 --port ${PORT}"]
