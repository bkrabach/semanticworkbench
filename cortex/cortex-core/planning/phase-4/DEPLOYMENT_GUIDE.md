# Deployment Guide for Cortex Core Phase 4

## Overview

This guide provides comprehensive instructions for deploying the distributed Cortex Core system developed in Phase 4. It covers building, configuring, and deploying the Memory Service, Cognition Service, and Core API components as independent services communicating over the network.

Phase 4 transforms the in-process MCP architecture established in Phase 3 into truly distributed services. This guide focuses on practical deployment steps, container management, environment configuration, and operational considerations to ensure a successful deployment.

## System Architecture Overview

The Phase 4 system consists of the following deployable components:

1. **Core API Application**: FastAPI application handling client interfaces
2. **Memory Service**: Standalone service for data storage and retrieval
3. **Cognition Service**: Standalone service for context generation

```
┌─────────────────┐                 ┌─────────────────┐
│                 │                 │                 │
│   Client Apps   │                 │     Client      │
│                 │                 │  Applications   │
└────────┬────────┘                 └────────┬────────┘
         │                                   │
         ▼                                   ▼
┌─────────────────┐                 ┌─────────────────┐
│                 │                 │                 │
│    Core API     │◄───────────────►│   Core API      │
│                 │                 │                 │
└────────┬────────┘                 └────────┬────────┘
         │                                   │
         ▼                                   │
┌─────────────────┐                          │
│  Service        │                          │
│  Discovery      │                          │
└────────┬────────┘                          │
         │                                   │
         ├───────────┬─────────────┐         │
         │           │             │         │
         ▼           ▼             ▼         │
┌─────────────┐ ┌─────────┐ ┌─────────────┐  │
│             │ │         │ │             │  │
│   Memory    │ │ Other   │ │ Cognition   │◄─┘
│   Service   │ │ Services│ │ Service     │
│             │ │         │ │             │
└─────────────┘ └─────────┘ └─────────────┘
```

Each service runs as an independent process, either on the same machine or across multiple machines, communicating via HTTP/SSE protocols.

## Prerequisites

Before beginning deployment, ensure you have the following prerequisites:

### System Requirements

- **Operating System**: Linux (Ubuntu 20.04+ recommended), macOS, or Windows with WSL2
- **CPU**: 2+ cores per service
- **Memory**: 2GB+ RAM per service
- **Disk**: 10GB+ available storage
- **Network**: Services must be able to communicate with each other

### Software Requirements

- **Docker**: v20.10.0 or higher
- **Docker Compose**: v2.0.0 or higher
- **Python**: v3.10 or higher (for local deployment only)
- **Git**: v2.25.0 or higher
- **Make**: v4.2.1 or higher (for build scripts)

### Account Requirements

- **Docker Hub** or private container registry access (for production)
- **Cloud provider account** (if deploying to cloud)

## Local Development Deployment

This section covers deploying the system locally for development and testing.

### Directory Structure

Set up your project directory structure as follows:

```
cortex-core/
├── app/                    # Core API application
├── memory-service/         # Memory Service
├── cognition-service/      # Cognition Service
├── deployment/
│   ├── docker-compose.yml  # Compose file for local deployment
│   ├── .env                # Environment variables
│   └── nginx/              # Optional reverse proxy configuration
└── scripts/
    ├── build.sh            # Build scripts
    └── deploy.sh           # Deployment scripts
```

### Environment Configuration

Create a `.env` file in the `deployment` directory with the following variables:

```ini
# Core API Configuration
CORE_API_PORT=8000
CORE_API_WORKERS=4
CORE_API_LOG_LEVEL=info

# Memory Service Configuration
MEMORY_SERVICE_PORT=9000
MEMORY_SERVICE_URL=http://memory-service:9000
MEMORY_DB_URL=sqlite:///memory.db

# Cognition Service Configuration
COGNITION_SERVICE_PORT=9100
COGNITION_SERVICE_URL=http://cognition-service:9100

# Service Discovery Configuration
SERVICE_DISCOVERY_REFRESH_INTERVAL=60

# Authentication Configuration
JWT_SECRET_KEY=your-secret-key-change-me
ACCESS_TOKEN_EXPIRE_HOURS=24

# Network Configuration
CONNECTION_TIMEOUT=10
MAX_RETRIES=3
CIRCUIT_BREAKER_THRESHOLD=5
```

> **IMPORTANT**: For development environments, these simplistic secrets are acceptable, but for any shared or production environment, use proper secret management and never commit secrets to version control.

### Building Containers

#### Core API Dockerfile

Create a `Dockerfile` in the root of your project:

```dockerfile
# Core API Dockerfile
FROM python:3.10-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

# Set Python environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

# Install Poetry
RUN pip install poetry==1.4.2

# Copy pyproject.toml and poetry.lock
COPY pyproject.toml poetry.lock* ./

# Configure poetry to not use virtualenvs
RUN poetry config virtualenvs.create false

# Install dependencies only (for layer caching)
RUN poetry install --no-interaction --no-ansi --no-root

# Copy application code
COPY . .

# Install application
RUN poetry install --no-interaction --no-ansi

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Set entrypoint
ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0"]
# Set default command (can be overridden)
CMD ["--port", "8000", "--workers", "4"]
```

#### Memory Service Dockerfile

Create a `Dockerfile` in the `memory-service` directory:

```dockerfile
# Memory Service Dockerfile
FROM python:3.10-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

# Set Python environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 9000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9000/health || exit 1

# Set entrypoint
ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0"]
# Set default command (can be overridden)
CMD ["--port", "9000", "--workers", "2"]
```

#### Cognition Service Dockerfile

Create a `Dockerfile` in the `cognition-service` directory:

```dockerfile
# Cognition Service Dockerfile
FROM python:3.10-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

# Set Python environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 9100

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9100/health || exit 1

# Set entrypoint
ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0"]
# Set default command (can be overridden)
CMD ["--port", "9100", "--workers", "2"]
```

#### Building the Containers

Create a `build.sh` script in the `scripts` directory:

```bash
#!/bin/bash

# Set base directory
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." >/dev/null 2>&1 && pwd)"

# Parse arguments
ENVIRONMENT=${1:-"development"}
VERSION=${2:-"latest"}

echo "Building containers for environment: $ENVIRONMENT, version: $VERSION"

# Build Core API
echo "Building Core API..."
docker build -t cortex-core:$VERSION -f $BASE_DIR/Dockerfile $BASE_DIR \
  --build-arg ENVIRONMENT=$ENVIRONMENT

# Build Memory Service
echo "Building Memory Service..."
docker build -t cortex-memory-service:$VERSION -f $BASE_DIR/memory-service/Dockerfile $BASE_DIR/memory-service \
  --build-arg ENVIRONMENT=$ENVIRONMENT

# Build Cognition Service
echo "Building Cognition Service..."
docker build -t cortex-cognition-service:$VERSION -f $BASE_DIR/cognition-service/Dockerfile $BASE_DIR/cognition-service \
  --build-arg ENVIRONMENT=$ENVIRONMENT

echo "Build completed."
```

Make the script executable:

```bash
chmod +x scripts/build.sh
```

Run the build script:

```bash
./scripts/build.sh
```

### Docker Compose Configuration

Create a `docker-compose.yml` file in the `deployment` directory:

```yaml
version: "3.8"

services:
  core-api:
    image: cortex-core:latest
    ports:
      - "${CORE_API_PORT:-8000}:8000"
    environment:
      - MEMORY_SERVICE_URL=${MEMORY_SERVICE_URL:-http://memory-service:9000}
      - COGNITION_SERVICE_URL=${COGNITION_SERVICE_URL:-http://cognition-service:9100}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY:-your-secret-key-change-me}
      - ACCESS_TOKEN_EXPIRE_HOURS=${ACCESS_TOKEN_EXPIRE_HOURS:-24}
      - CONNECTION_TIMEOUT=${CONNECTION_TIMEOUT:-10}
      - MAX_RETRIES=${MAX_RETRIES:-3}
      - CIRCUIT_BREAKER_THRESHOLD=${CIRCUIT_BREAKER_THRESHOLD:-5}
      - LOG_LEVEL=${CORE_API_LOG_LEVEL:-info}
    volumes:
      - core-api-data:/data
    depends_on:
      - memory-service
      - cognition-service
    restart: unless-stopped
    networks:
      - cortex-network
    command: --port 8000 --workers ${CORE_API_WORKERS:-4}

  memory-service:
    image: cortex-memory-service:latest
    ports:
      - "${MEMORY_SERVICE_PORT:-9000}:9000"
    environment:
      - MEMORY_DB_URL=${MEMORY_DB_URL:-sqlite:///data/memory.db}
      - LOG_LEVEL=${MEMORY_SERVICE_LOG_LEVEL:-info}
    volumes:
      - memory-service-data:/data
    restart: unless-stopped
    networks:
      - cortex-network
    command: --port 9000 --workers 2

  cognition-service:
    image: cortex-cognition-service:latest
    ports:
      - "${COGNITION_SERVICE_PORT:-9100}:9100"
    environment:
      - MEMORY_SERVICE_URL=${MEMORY_SERVICE_URL:-http://memory-service:9000}
      - LOG_LEVEL=${COGNITION_SERVICE_LOG_LEVEL:-info}
    restart: unless-stopped
    networks:
      - cortex-network
    command: --port 9100 --workers 2

networks:
  cortex-network:
    driver: bridge

volumes:
  core-api-data:
  memory-service-data:
```

### Starting the Services

Create a `deploy.sh` script in the `scripts` directory:

```bash
#!/bin/bash

# Set base directory
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." >/dev/null 2>&1 && pwd)"

# Parse arguments
ACTION=${1:-"up"}
ENVIRONMENT=${2:-"development"}

# Load environment variables
if [ -f "$BASE_DIR/deployment/.env" ]; then
  export $(grep -v '^#' $BASE_DIR/deployment/.env | xargs)
fi

# Change to deployment directory
cd $BASE_DIR/deployment

# Execute action
case $ACTION in
  up)
    echo "Starting services..."
    docker-compose up -d
    ;;
  down)
    echo "Stopping services..."
    docker-compose down
    ;;
  restart)
    echo "Restarting services..."
    docker-compose restart
    ;;
  logs)
    echo "Showing logs..."
    docker-compose logs -f
    ;;
  *)
    echo "Unknown action: $ACTION"
    echo "Usage: $0 [up|down|restart|logs] [environment]"
    exit 1
    ;;
esac

echo "Done."
```

Make the script executable:

```bash
chmod +x scripts/deploy.sh
```

Start the services:

```bash
./scripts/deploy.sh up
```

Check the logs:

```bash
./scripts/deploy.sh logs
```

Stop the services:

```bash
./scripts/deploy.sh down
```

### Verifying Deployment

Once the services are running, you should verify the deployment:

1. **Check Container Status**:

   ```bash
   docker ps
   ```

   Verify all three containers are running.

2. **Check Health Endpoints**:

   ```bash
   curl http://localhost:8000/health
   curl http://localhost:9000/health
   curl http://localhost:9100/health
   ```

   All endpoints should return a 200 OK response with a status of "healthy".

3. **Test Basic Functionality**:

   ```bash
   # Get a token
   curl -X POST http://localhost:8000/auth/login \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=user@example.com&password=password123"

   # Use the token to make a request
   curl -X POST http://localhost:8000/input \
     -H "Authorization: Bearer YOUR_TOKEN_HERE" \
     -H "Content-Type: application/json" \
     -d '{"content": "Hello, Cortex!"}'
   ```

## Production Deployment

This section covers deploying the system in a production environment.

### Production Considerations

When deploying to production, consider the following:

1. **Secret Management**: Use a proper secrets management system
2. **SSL/TLS**: Configure SSL/TLS for all service communications
3. **High Availability**: Deploy multiple instances of each service
4. **Database**: Use a managed database service instead of SQLite
5. **Monitoring**: Set up comprehensive monitoring and alerting
6. **Backup**: Implement regular data backups
7. **Security**: Harden container security
8. **Network**: Implement proper network security
9. **Resource Limits**: Configure appropriate resource limits
10. **Scaling**: Implement auto-scaling policies

### Container Registry

For production, push your containers to a container registry:

```bash
# Tag images for registry
docker tag cortex-core:latest your-registry.example.com/cortex-core:latest
docker tag cortex-memory-service:latest your-registry.example.com/cortex-memory-service:latest
docker tag cortex-cognition-service:latest your-registry.example.com/cortex-cognition-service:latest

# Push to registry
docker push your-registry.example.com/cortex-core:latest
docker push your-registry.example.com/cortex-memory-service:latest
docker push your-registry.example.com/cortex-cognition-service:latest
```

### Production Docker Compose

For a more production-ready Docker Compose configuration, create a `docker-compose.prod.yml` file:

```yaml
version: "3.8"

services:
  core-api:
    image: your-registry.example.com/cortex-core:latest
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: "1"
          memory: 1G
        reservations:
          cpus: "0.5"
          memory: 512M
      restart_policy:
        condition: on-failure
        max_attempts: 3
    environment:
      - MEMORY_SERVICE_URL=http://memory-service:9000
      - COGNITION_SERVICE_URL=http://cognition-service:9100
      # Use secrets for sensitive values in production
    secrets:
      - jwt_secret_key
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    networks:
      - cortex-network

  memory-service:
    image: your-registry.example.com/cortex-memory-service:latest
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: "1"
          memory: 1G
        reservations:
          cpus: "0.5"
          memory: 512M
      restart_policy:
        condition: on-failure
        max_attempts: 3
    environment:
      - MEMORY_DB_URL=postgres://user:password@db:5432/memory
    secrets:
      - db_password
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    networks:
      - cortex-network

  cognition-service:
    image: your-registry.example.com/cortex-cognition-service:latest
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: "1"
          memory: 1G
        reservations:
          cpus: "0.5"
          memory: 512M
      restart_policy:
        condition: on-failure
        max_attempts: 3
    environment:
      - MEMORY_SERVICE_URL=http://memory-service:9000
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    networks:
      - cortex-network

  nginx:
    image: nginx:latest
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/certs:/etc/nginx/certs:ro
    deploy:
      replicas: 1
      restart_policy:
        condition: on-failure
    depends_on:
      - core-api
    networks:
      - cortex-network

networks:
  cortex-network:
    driver: overlay

secrets:
  jwt_secret_key:
    external: true
  db_password:
    external: true
```

### Kubernetes Deployment

For production environments, Kubernetes is often a better choice. Here are example Kubernetes YAML files:

#### Core API Deployment

Create a `core-api-deployment.yaml` file:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: core-api
  labels:
    app: core-api
spec:
  replicas: 2
  selector:
    matchLabels:
      app: core-api
  template:
    metadata:
      labels:
        app: core-api
    spec:
      containers:
        - name: core-api
          image: your-registry.example.com/cortex-core:latest
          ports:
            - containerPort: 8000
          env:
            - name: MEMORY_SERVICE_URL
              value: "http://memory-service:9000"
            - name: COGNITION_SERVICE_URL
              value: "http://cognition-service:9100"
            - name: JWT_SECRET_KEY
              valueFrom:
                secretKeyRef:
                  name: cortex-secrets
                  key: jwt-secret-key
          resources:
            limits:
              cpu: "1"
              memory: "1Gi"
            requests:
              cpu: "500m"
              memory: "512Mi"
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 5
      restartPolicy: Always
```

Create a `core-api-service.yaml` file:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: core-api
spec:
  selector:
    app: core-api
  ports:
    - port: 8000
      targetPort: 8000
  type: ClusterIP
```

#### Memory Service Deployment

Create a `memory-service-deployment.yaml` file:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: memory-service
  labels:
    app: memory-service
spec:
  replicas: 2
  selector:
    matchLabels:
      app: memory-service
  template:
    metadata:
      labels:
        app: memory-service
    spec:
      containers:
        - name: memory-service
          image: your-registry.example.com/cortex-memory-service:latest
          ports:
            - containerPort: 9000
          env:
            - name: MEMORY_DB_URL
              valueFrom:
                secretKeyRef:
                  name: cortex-secrets
                  key: memory-db-url
          resources:
            limits:
              cpu: "1"
              memory: "1Gi"
            requests:
              cpu: "500m"
              memory: "512Mi"
          livenessProbe:
            httpGet:
              path: /health
              port: 9000
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health
              port: 9000
            initialDelaySeconds: 5
            periodSeconds: 5
      restartPolicy: Always
```

Create a `memory-service-service.yaml` file:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: memory-service
spec:
  selector:
    app: memory-service
  ports:
    - port: 9000
      targetPort: 9000
  type: ClusterIP
```

#### Cognition Service Deployment

Create a `cognition-service-deployment.yaml` file:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cognition-service
  labels:
    app: cognition-service
spec:
  replicas: 2
  selector:
    matchLabels:
      app: cognition-service
  template:
    metadata:
      labels:
        app: cognition-service
    spec:
      containers:
        - name: cognition-service
          image: your-registry.example.com/cortex-cognition-service:latest
          ports:
            - containerPort: 9100
          env:
            - name: MEMORY_SERVICE_URL
              value: "http://memory-service:9000"
          resources:
            limits:
              cpu: "1"
              memory: "1Gi"
            requests:
              cpu: "500m"
              memory: "512Mi"
          livenessProbe:
            httpGet:
              path: /health
              port: 9100
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health
              port: 9100
            initialDelaySeconds: 5
            periodSeconds: 5
      restartPolicy: Always
```

Create a `cognition-service-service.yaml` file:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: cognition-service
spec:
  selector:
    app: cognition-service
  ports:
    - port: 9100
      targetPort: 9100
  type: ClusterIP
```

#### Ingress Configuration

Create a `cortex-ingress.yaml` file:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: cortex-ingress
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  ingressClassName: nginx
  rules:
    - host: cortex.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: core-api
                port:
                  number: 8000
  tls:
    - hosts:
        - cortex.example.com
      secretName: cortex-tls-secret
```

#### Secrets Management

Create a `cortex-secrets.yaml` file:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: cortex-secrets
type: Opaque
stringData:
  jwt-secret-key: <your-jwt-secret>
  memory-db-url: postgres://user:<db-password>@postgres:5432/memory
```

> **IMPORTANT**: Never commit this file to version control. In production, consider using a secrets management solution like HashiCorp Vault or Kubernetes native secrets management.

#### Applying Kubernetes Configuration

Apply the configurations:

```bash
kubectl apply -f core-api-deployment.yaml
kubectl apply -f core-api-service.yaml
kubectl apply -f memory-service-deployment.yaml
kubectl apply -f memory-service-service.yaml
kubectl apply -f cognition-service-deployment.yaml
kubectl apply -f cognition-service-service.yaml
kubectl apply -f cortex-ingress.yaml
kubectl apply -f cortex-secrets.yaml
```

## Service Configuration

### Core API Configuration

The Core API service accepts the following configuration parameters through environment variables:

| Variable                    | Description                                 | Default Value                   |
| --------------------------- | ------------------------------------------- | ------------------------------- |
| `MEMORY_SERVICE_URL`        | URL of the Memory Service                   | `http://memory-service:9000`    |
| `COGNITION_SERVICE_URL`     | URL of the Cognition Service                | `http://cognition-service:9100` |
| `JWT_SECRET_KEY`            | Secret key for JWT token generation         | `your-secret-key-change-me`     |
| `ACCESS_TOKEN_EXPIRE_HOURS` | JWT token expiration in hours               | `24`                            |
| `CONNECTION_TIMEOUT`        | HTTP connection timeout in seconds          | `10`                            |
| `MAX_RETRIES`               | Maximum number of request retries           | `3`                             |
| `CIRCUIT_BREAKER_THRESHOLD` | Failed requests before circuit opens        | `5`                             |
| `LOG_LEVEL`                 | Logging level (debug, info, warning, error) | `info`                          |

### Memory Service Configuration

The Memory Service accepts the following configuration parameters through environment variables:

| Variable        | Description                                 | Default Value              |
| --------------- | ------------------------------------------- | -------------------------- |
| `MEMORY_DB_URL` | Database connection string                  | `sqlite:///data/memory.db` |
| `LOG_LEVEL`     | Logging level (debug, info, warning, error) | `info`                     |

### Cognition Service Configuration

The Cognition Service accepts the following configuration parameters through environment variables:

| Variable             | Description                                 | Default Value                |
| -------------------- | ------------------------------------------- | ---------------------------- |
| `MEMORY_SERVICE_URL` | URL of the Memory Service                   | `http://memory-service:9000` |
| `LOG_LEVEL`          | Logging level (debug, info, warning, error) | `info`                       |

## Scaling

### Horizontal Scaling

For horizontal scaling, you can increase the number of replicas for each service:

**Docker Compose**:

```bash
docker-compose up --scale core-api=3 --scale memory-service=2 --scale cognition-service=2
```

**Kubernetes**:

```bash
kubectl scale deployment core-api --replicas=3
kubectl scale deployment memory-service --replicas=2
kubectl scale deployment cognition-service --replicas=2
```

### Vertical Scaling

For vertical scaling, adjust the resource limits in your deployment configuration.

### Scaling Considerations

- **Core API**: Scales horizontally with minimal shared state
- **Memory Service**: Database becomes a potential bottleneck, consider database scaling
- **Cognition Service**: Scales horizontally but may require more memory per instance

## Monitoring and Logging

### Prometheus Metrics

Each service exposes metrics on the `/metrics` endpoint. Configure Prometheus to scrape these endpoints.

Example Prometheus configuration:

```yaml
scrape_configs:
  - job_name: "cortex-core"
    scrape_interval: 15s
    static_configs:
      - targets: ["core-api:8000"]
  - job_name: "cortex-memory"
    scrape_interval: 15s
    static_configs:
      - targets: ["memory-service:9000"]
  - job_name: "cortex-cognition"
    scrape_interval: 15s
    static_configs:
      - targets: ["cognition-service:9100"]
```

### Log Management

Configure centralized logging using a solution like ELK Stack or Grafana Loki.

Example Docker logging configuration:

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

For production, consider using a log aggregation service.

## Backup and Recovery

### Database Backup

For the Memory Service database:

```bash
# SQLite backup
docker exec memory-service sh -c "sqlite3 /data/memory.db .dump > /data/backup.sql"

# PostgreSQL backup
docker exec memory-service sh -c "pg_dump -U user -d memory > /data/backup.sql"
```

### Recovery Procedure

```bash
# SQLite recovery
docker exec memory-service sh -c "sqlite3 /data/memory.db < /data/backup.sql"

# PostgreSQL recovery
docker exec memory-service sh -c "psql -U user -d memory < /data/backup.sql"
```

## Security

### Environment Hardening

1. **Use non-root users in containers**:

   ```dockerfile
   # Add to Dockerfiles
   RUN adduser --disabled-password --gecos "" app
   USER app
   ```

2. **Restrict container capabilities**:

   ```yaml
   # Add to Docker Compose
   security_opt:
     - no-new-privileges:true
   cap_drop:
     - ALL
   ```

3. **Use read-only file systems**:
   ```yaml
   # Add to Docker Compose
   read_only: true
   ```

### Network Security

1. **Use internal networks for service communication**:

   ```yaml
   # Add to Docker Compose
   networks:
     frontend:
       internal: false
     backend:
       internal: true
   ```

2. **Configure HTTPS for all services**
3. **Implement network policies to restrict communication**

### Secret Management

1. **Use environment variables for non-sensitive configuration**
2. **Use secrets management for sensitive information**
3. **Rotate secrets regularly**

## Troubleshooting

### Common Issues

#### Service Discovery Issues

**Symptom**: Services cannot find each other
**Solution**: Check environment variables and network configuration

```bash
# Verify service discovery
docker exec core-api curl -f http://memory-service:9000/health
docker exec core-api curl -f http://cognition-service:9100/health
```

#### Database Connection Issues

**Symptom**: Memory Service fails to start or returns errors
**Solution**: Check database connection string and database availability

```bash
# Check database connection
docker exec memory-service python -c "import sqlalchemy; print(sqlalchemy.create_engine('$MEMORY_DB_URL').connect())"
```

#### Container Startup Issues

**Symptom**: Containers fail to start or crash immediately
**Solution**: Check logs and environment configuration

```bash
# Check container logs
docker logs memory-service
```

### Accessing Container Shells

For debugging:

```bash
docker exec -it core-api bash
docker exec -it memory-service bash
docker exec -it cognition-service bash
```

### Checking Health Endpoints

```bash
curl http://localhost:8000/health
curl http://localhost:9000/health
curl http://localhost:9100/health
```

## Deployment Checklist

Use this checklist before and after deployment:

### Pre-Deployment

- [ ] Code pushed to repository
- [ ] Containers built and tested locally
- [ ] Environment variables configured
- [ ] Secrets configured
- [ ] Network configuration verified
- [ ] Database prepared
- [ ] Storage volumes created

### Post-Deployment

- [ ] All containers running
- [ ] Health checks passing
- [ ] API endpoints accessible
- [ ] Service-to-service communication working
- [ ] Logs being generated correctly
- [ ] Metrics being collected
- [ ] Backup procedure tested

## Conclusion

This deployment guide provides a comprehensive approach to deploying the Cortex Core distributed system. By following these instructions, you should be able to successfully deploy the system in both development and production environments.

Key considerations for a successful deployment:

1. **Environment Configuration**: Ensure all environment variables are properly set
2. **Container Security**: Follow security best practices for container deployment
3. **Monitoring**: Implement proper monitoring and logging
4. **Scaling**: Consider your scaling strategy based on workload
5. **Backup**: Implement and test backup procedures
6. **Testing**: Thoroughly test the deployment before going live

The distributed architecture of Phase 4 provides a solid foundation for scaling and extending the Cortex Core system while maintaining clear service boundaries and responsibilities.
