FROM python:3.13-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir fastapi uvicorn[standard] itsdangerous bcrypt pyyaml

# Copy source code
COPY . /app

# Expose dashboard port
EXPOSE 8443

# Environment — HERMES_HOME must be set at runtime (read-only volume mount)
ENV HERMES_HOME=/data

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8443", "--log-level", "warning"]
