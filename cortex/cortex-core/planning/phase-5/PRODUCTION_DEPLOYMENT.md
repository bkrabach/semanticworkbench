# Production Deployment Guide

## Overview

This document provides comprehensive guidance for deploying the Cortex Core platform to production environments in Phase 5. It covers container-based deployment strategies, environment configuration, secrets management, database initialization, zero-downtime deployment, scaling strategies, and infrastructure as code.

The production deployment process builds upon the distributed services architecture established in Phase 4, now enhanced with enterprise-grade features such as Azure B2C authentication, PostgreSQL databases, comprehensive error handling, logging, monitoring, and security hardening.

## Deployment Architecture

The production deployment architecture consists of the following components:

```mermaid
graph TD
    Client[Client Applications] -->|HTTPS| INGRESS[Ingress Controller]
    INGRESS --> API[Cortex Core API]
    API --> MemoryService[Memory Service]
    API --> CognitionService[Cognition Service]

    API --> CoreDB[(PostgreSQL Core DB)]
    MemoryService --> MemoryDB[(PostgreSQL Memory DB)]

    API --> AZUREB2C[Azure B2C]

    Monitoring[Monitoring Stack] -.-> API
    Monitoring -.-> MemoryService
    Monitoring -.-> CognitionService

    subgraph "Kubernetes Cluster"
        INGRESS
        API
        MemoryService
        CognitionService
    end

    subgraph "Database Cluster"
        CoreDB
        MemoryDB
    end

    subgraph "External Services"
        AZUREB2C
    end

    subgraph "Monitoring"
        Monitoring
    end
```

### Key Architectural Components

1. **Ingress Controller**: Routes external traffic to internal services
2. **Cortex Core API**: Main API service for client interaction
3. **Memory Service**: Stores and retrieves user data
4. **Cognition Service**: Processes context and provides insights
5. **PostgreSQL Databases**: Production-grade persistent storage
6. **Azure B2C**: Enterprise authentication provider
7. **Monitoring Stack**: Observability and alerting

## Infrastructure Requirements

### Compute Resources

| Component           | Instances | CPU (min) | CPU (recommended) | Memory (min) | Memory (recommended) | Disk Space |
| ------------------- | --------- | --------- | ----------------- | ------------ | -------------------- | ---------- |
| Cortex Core API     | 2+        | 1 core    | 2 cores           | 2 GB         | 4 GB                 | 20 GB      |
| Memory Service      | 2+        | 1 core    | 2 cores           | 4 GB         | 8 GB                 | 20 GB      |
| Cognition Service   | 2+        | 2 cores   | 4 cores           | 4 GB         | 8 GB                 | 20 GB      |
| PostgreSQL (Core)   | 2         | 2 cores   | 4 cores           | 4 GB         | 8 GB                 | 100 GB     |
| PostgreSQL (Memory) | 2         | 2 cores   | 4 cores           | 8 GB         | 16 GB                | 500 GB     |
| Monitoring Stack    | 1         | 2 cores   | 4 cores           | 4 GB         | 8 GB                 | 100 GB     |

### Network Requirements

| Connection Path                      | Protocol   | Port    | Traffic Pattern | Encryption       |
| ------------------------------------ | ---------- | ------- | --------------- | ---------------- |
| Client → Ingress                     | HTTPS      | 443     | Bidirectional   | TLS 1.2+         |
| Ingress → API                        | HTTP       | 8000    | Bidirectional   | Cluster internal |
| API → Memory Service                 | HTTP       | 9000    | Bidirectional   | Cluster internal |
| API → Cognition Service              | HTTP       | 9100    | Bidirectional   | Cluster internal |
| API → PostgreSQL (Core)              | PostgreSQL | 5432    | Bidirectional   | TLS              |
| Memory Service → PostgreSQL (Memory) | PostgreSQL | 5432    | Bidirectional   | TLS              |
| API → Azure B2C                      | HTTPS      | 443     | Bidirectional   | TLS 1.2+         |
| All Services → Monitoring            | HTTP       | Various | Unidirectional  | Cluster internal |

### Storage Requirements

1. **PostgreSQL Core Database**:

   - Initial Size: 20 GB
   - Growth Rate: ~1 GB per 10,000 users per month
   - Backup: Daily full backups, continuous WAL archiving

2. **PostgreSQL Memory Database**:

   - Initial Size: 100 GB
   - Growth Rate: ~5 GB per 10,000 users per month
   - Backup: Daily full backups, continuous WAL archiving

3. **Service Logs**:

   - Retention: 30 days
   - Size: ~2 GB per day for all services combined
   - Archival: Compressed and archived after 7 days

4. **Monitoring Data**:
   - Metrics Retention: 30 days
   - Size: ~1 GB per day
   - Alerts History: 90 days

## Container-Based Deployment

### Container Configuration

#### Cortex Core API Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV SERVICE_NAME=cortex-core

# Expose the service port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8000/health/live || exit 1

# Run with gunicorn
CMD ["gunicorn", "app.main:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
```

#### Memory Service Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV SERVICE_NAME=memory-service

# Expose the service port
EXPOSE 9000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:9000/health/live || exit 1

# Run with gunicorn
CMD ["gunicorn", "app.main:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:9000"]
```

#### Cognition Service Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV SERVICE_NAME=cognition-service

# Expose the service port
EXPOSE 9100

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:9100/health/live || exit 1

# Run with gunicorn
CMD ["gunicorn", "app.main:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:9100"]
```

### Container Best Practices

1. **Use specific image versions**: Always specify exact versions for base images
2. **Multi-stage builds**: Use multi-stage builds for smaller final images
3. **Non-root users**: Run containers as non-root users for security
4. **Health checks**: Implement container health checks
5. **Proper signal handling**: Ensure graceful shutdowns
6. **Resource limits**: Set memory and CPU limits
7. **Labeled images**: Add metadata labels for tracking
8. **Layer caching**: Order Dockerfile instructions to optimize caching
9. **Security scanning**: Scan images for vulnerabilities before deployment

### Example of a more secure Dockerfile

```dockerfile
# Build stage
FROM python:3.10-slim AS builder

WORKDIR /build

# Install build dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Runtime stage
FROM python:3.10-slim

# Create non-root user
RUN groupadd -r cortex && useradd -r -g cortex cortex

# Set working directory
WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /root/.local /home/cortex/.local
ENV PATH=/home/cortex/.local/bin:$PATH

# Copy application code
COPY --chown=cortex:cortex . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV SERVICE_NAME=cortex-core
ENV PATH="/home/cortex/.local/bin:$PATH"

# Set user
USER cortex

# Expose the service port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8000/health/live || exit 1

# Add metadata labels
LABEL maintainer="your-team@example.com"
LABEL version="1.0.0"
LABEL description="Cortex Core API Service"

# Run with gunicorn
CMD ["gunicorn", "app.main:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
```

## Kubernetes Deployment

### Namespace Setup

Create dedicated namespaces for different components:

```yaml
# namespaces.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cortex-core
  labels:
    name: cortex-core

---
apiVersion: v1
kind: Namespace
metadata:
  name: cortex-monitoring
  labels:
    name: cortex-monitoring
```

### Deployment Configurations

#### Cortex Core API Deployment

```yaml
# cortex-core-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cortex-core-api
  namespace: cortex-core
spec:
  replicas: 3
  selector:
    matchLabels:
      app: cortex-core-api
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: cortex-core-api
    spec:
      containers:
        - name: cortex-core-api
          image: ${CONTAINER_REGISTRY}/cortex-core-api:${VERSION}
          ports:
            - containerPort: 8000
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: cortex-core-secrets
                  key: core-db-url
            - name: SERVICE_NAME
              value: "cortex-core-api"
            - name: LOG_LEVEL
              value: "INFO"
            - name: MEMORY_SERVICE_URL
              value: "http://memory-service:9000"
            - name: COGNITION_SERVICE_URL
              value: "http://cognition-service:9100"
            - name: B2C_TENANT_ID
              valueFrom:
                secretKeyRef:
                  name: cortex-core-secrets
                  key: b2c-tenant-id
            - name: B2C_CLIENT_ID
              valueFrom:
                secretKeyRef:
                  name: cortex-core-secrets
                  key: b2c-client-id
            - name: B2C_CLIENT_SECRET
              valueFrom:
                secretKeyRef:
                  name: cortex-core-secrets
                  key: b2c-client-secret
            - name: B2C_POLICY
              valueFrom:
                secretKeyRef:
                  name: cortex-core-secrets
                  key: b2c-policy
          resources:
            requests:
              memory: "2Gi"
              cpu: "1"
            limits:
              memory: "4Gi"
              cpu: "2"
          readinessProbe:
            httpGet:
              path: /health/ready
              port: 8000
            initialDelaySeconds: 15
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /health/live
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 20
          startupProbe:
            httpGet:
              path: /health/live
              port: 8000
            failureThreshold: 30
            periodSeconds: 10
      securityContext:
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
```

#### Memory Service Deployment

```yaml
# memory-service-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: memory-service
  namespace: cortex-core
spec:
  replicas: 3
  selector:
    matchLabels:
      app: memory-service
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: memory-service
    spec:
      containers:
        - name: memory-service
          image: ${CONTAINER_REGISTRY}/memory-service:${VERSION}
          ports:
            - containerPort: 9000
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: cortex-core-secrets
                  key: memory-db-url
            - name: SERVICE_NAME
              value: "memory-service"
            - name: LOG_LEVEL
              value: "INFO"
          resources:
            requests:
              memory: "4Gi"
              cpu: "1"
            limits:
              memory: "8Gi"
              cpu: "2"
          readinessProbe:
            httpGet:
              path: /health/ready
              port: 9000
            initialDelaySeconds: 15
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /health/live
              port: 9000
            initialDelaySeconds: 30
            periodSeconds: 20
          startupProbe:
            httpGet:
              path: /health/live
              port: 9000
            failureThreshold: 30
            periodSeconds: 10
      securityContext:
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
```

### Service Configurations

#### Cortex Core API Service

```yaml
# cortex-core-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: cortex-core-api
  namespace: cortex-core
spec:
  selector:
    app: cortex-core-api
  ports:
    - name: http
      port: 8000
      targetPort: 8000
  type: ClusterIP
```

#### Memory Service Service

```yaml
# memory-service-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: memory-service
  namespace: cortex-core
spec:
  selector:
    app: memory-service
  ports:
    - name: http
      port: 9000
      targetPort: 9000
  type: ClusterIP
```

### Ingress Configuration

```yaml
# cortex-core-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: cortex-core-ingress
  namespace: cortex-core
  annotations:
    kubernetes.io/ingress.class: "nginx"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "120"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "120"
    nginx.ingress.kubernetes.io/server-snippet: |
      add_header X-Content-Type-Options "nosniff" always;
      add_header X-Frame-Options "DENY" always;
      add_header X-XSS-Protection "1; mode=block" always;
      add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
spec:
  tls:
    - hosts:
        - api.cortex-core.example.com
      secretName: cortex-core-tls
  rules:
    - host: api.cortex-core.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: cortex-core-api
                port:
                  name: http
```

### ConfigMaps and Secrets

#### ConfigMap for application settings

```yaml
# cortex-core-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cortex-core-config
  namespace: cortex-core
data:
  ENVIRONMENT: "production"
  LOG_LEVEL: "INFO"
  LOG_FORMAT: "json"
  REQUIRE_HTTPS: "true"
  ALLOWED_HOSTS: "api.cortex-core.example.com"
  CORS_ORIGINS: "https://app.cortex-core.example.com"
  DB_POOL_SIZE: "10"
  DB_MAX_OVERFLOW: "20"
  DB_POOL_TIMEOUT: "30"
  DB_POOL_RECYCLE: "1800"
```

#### Secrets (using sealed secrets or a vault solution)

```yaml
# Example of how you would create secrets (don't store these in git)
kubectl create secret generic cortex-core-secrets \
--from-literal=core-db-url="postgresql+asyncpg://username:password@postgres-core:5432/cortex_core" \
--from-literal=memory-db-url="postgresql+asyncpg://username:password@postgres-memory:5432/cortex_memory" \
--from-literal=b2c-tenant-id="your-tenant-id" \
--from-literal=b2c-client-id="your-client-id" \
--from-literal=b2c-client-secret="your-client-secret" \
--from-literal=b2c-policy="B2C_1_SignUpSignIn"
```

## Environment Configuration Management

### Environment Variables

Define environment variables for different environments:

| Variable        | Development | Staging                     | Production              |
| --------------- | ----------- | --------------------------- | ----------------------- |
| ENVIRONMENT     | development | staging                     | production              |
| LOG_LEVEL       | DEBUG       | INFO                        | INFO                    |
| DB_POOL_SIZE    | 5           | 10                          | 10                      |
| DB_MAX_OVERFLOW | 10          | 15                          | 20                      |
| CORS_ORIGINS    | \*          | https://staging.example.com | https://app.example.com |
| REQUIRE_HTTPS   | false       | true                        | true                    |

### Configuration Loading Strategy

Use a hierarchical configuration loading strategy:

1. **Default values**: Hardcoded in application
2. **Config files**: Loaded from a predefined location
3. **Environment variables**: Override file-based configuration
4. **Command-line arguments**: Highest priority overrides

```python
# Example configuration loading pattern
import os
import argparse
import yaml
from typing import Dict, Any

def load_configuration() -> Dict[str, Any]:
    """
    Load configuration in this order of precedence:
    1. Command-line arguments
    2. Environment variables
    3. Config file
    4. Default values
    """
    # Start with default values
    config = {
        "environment": "development",
        "log_level": "INFO",
        "database_url": "sqlite:///./app.db",
        "require_https": False,
        "allowed_hosts": ["localhost"],
        "cors_origins": ["*"],
        # More defaults...
    }

    # Load from config file if it exists
    config_file = os.getenv("CONFIG_FILE", "/etc/cortex-core/config.yaml")
    if os.path.exists(config_file):
        with open(config_file, "r") as f:
            file_config = yaml.safe_load(f)
            if file_config:
                config.update(file_config)

    # Override with environment variables
    env_mapping = {
        "ENVIRONMENT": "environment",
        "LOG_LEVEL": "log_level",
        "DATABASE_URL": "database_url",
        "REQUIRE_HTTPS": "require_https",
        "ALLOWED_HOSTS": "allowed_hosts",
        "CORS_ORIGINS": "cors_origins",
        # More mappings...
    }

    for env_var, config_key in env_mapping.items():
        if env_var in os.environ:
            # Handle type conversion
            if config_key in ["require_https"]:
                config[config_key] = os.getenv(env_var).lower() == "true"
            elif config_key in ["allowed_hosts", "cors_origins"]:
                config[config_key] = os.getenv(env_var).split(",")
            else:
                config[config_key] = os.getenv(env_var)

    # Override with command-line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment", help="Deployment environment")
    parser.add_argument("--log-level", help="Logging level")
    # More arguments...

    args = parser.parse_args()
    arg_dict = {k: v for k, v in vars(args).items() if v is not None}

    # Convert snake_case args to config keys
    for arg_key, arg_value in arg_dict.items():
        config_key = arg_key.replace("-", "_")
        config[config_key] = arg_value

    return config
```

## Secrets Management

### Kubernetes Secrets

For basic secrets management, use Kubernetes Secrets:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: database-credentials
  namespace: cortex-core
type: Opaque
data:
  username: <base64-encoded-username>
  password: <base64-encoded-password>
```

### External Secrets Management

For production, use a dedicated secrets management solution:

1. **HashiCorp Vault**: Enterprise-grade secrets management
2. **AWS Secrets Manager**: Cloud-native solution for AWS
3. **Azure Key Vault**: Cloud-native solution for Azure
4. **Sealed Secrets**: Kubernetes-native encrypted secrets

#### Using External Secrets Operator with AWS Secrets Manager

```yaml
# external-secret.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: database-credentials
  namespace: cortex-core
spec:
  refreshInterval: "15m"
  secretStoreRef:
    name: aws-secretsmanager
    kind: ClusterSecretStore
  target:
    name: database-credentials
    creationPolicy: Owner
  data:
    - secretKey: username
      remoteRef:
        key: cortex-core/database
        property: username
    - secretKey: password
      remoteRef:
        key: cortex-core/database
        property: password
```

### Secrets Rotation

Implement secrets rotation for enhanced security:

1. **Define rotation policy**: Determine how often secrets should be rotated
2. **Implement rotation mechanism**: Use automated tools or scripts
3. **Handle graceful transitions**: Ensure services can handle secret changes
4. **Monitor rotation events**: Log and verify successful rotations

## Database Initialization and Migration

### PostgreSQL Setup

#### Initial Database Setup

```bash
#!/bin/bash
# initialize-db.sh

# Variables
DB_HOST=${DB_HOST:-postgres}
DB_PORT=${DB_PORT:-5432}
DB_USER=${DB_USER:-postgres}
DB_PASSWORD=${DB_PASSWORD:-password}
DB_NAME=${DB_NAME:-cortex_core}

# Create database if it doesn't exist
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -tc \
  "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1 || \
  PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -c "CREATE DATABASE $DB_NAME"

# Create extensions
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "CREATE EXTENSION IF NOT EXISTS pgcrypto;"
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"

echo "Database initialized successfully"
```

### Alembic Migration Strategy

1. **Initialize Alembic**: Set up migration environment

   ```bash
   alembic init migrations
   ```

2. **Configure Alembic**: Update configuration for PostgreSQL

   ```python
   # alembic.ini
   sqlalchemy.url = postgresql+asyncpg://%(DB_USER)s:%(DB_PASSWORD)s@%(DB_HOST)s:%(DB_PORT)s/%(DB_NAME)s
   ```

3. **Create Migration Scripts**: Generate migration scripts

   ```bash
   alembic revision --autogenerate -m "Create initial tables"
   ```

4. **Apply Migrations**: Run migrations during deployment

   ```bash
   alembic upgrade head
   ```

### Kubernetes Jobs for Database Migrations

```yaml
# db-migration-job.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migration-job
  namespace: cortex-core
spec:
  ttlSecondsAfterFinished: 100
  template:
    spec:
      containers:
        - name: db-migration
          image: ${CONTAINER_REGISTRY}/cortex-core-api:${VERSION}
          command: ["alembic", "upgrade", "head"]
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: cortex-core-secrets
                  key: core-db-url
      restartPolicy: Never
  backoffLimit: 4
```

## Deployment Workflow

### CI/CD Pipeline

```yaml
# Example GitLab CI/CD pipeline
stages:
  - build
  - test
  - deploy

variables:
  CONTAINER_REGISTRY: "registry.example.com"
  KUBERNETES_NAMESPACE: "cortex-core"

build:
  stage: build
  script:
    - docker build -t $CONTAINER_REGISTRY/cortex-core-api:$CI_COMMIT_SHORT_SHA .
    - docker push $CONTAINER_REGISTRY/cortex-core-api:$CI_COMMIT_SHORT_SHA

test:
  stage: test
  script:
    - pip install -r requirements.txt
    - pip install -r requirements-dev.txt
    - pytest

deploy_staging:
  stage: deploy
  environment: staging
  script:
    - kubectl config use-context staging
    - envsubst < k8s/cortex-core-deployment.yaml | kubectl apply -f -
    - kubectl rollout status deployment/cortex-core-api -n $KUBERNETES_NAMESPACE
  rules:
    - if: $CI_COMMIT_BRANCH == "main"

deploy_production:
  stage: deploy
  environment: production
  script:
    - kubectl config use-context production
    - envsubst < k8s/cortex-core-deployment.yaml | kubectl apply -f -
    - kubectl rollout status deployment/cortex-core-api -n $KUBERNETES_NAMESPACE
  rules:
    - if: $CI_COMMIT_TAG
  when: manual
```

### Deployment Steps

1. **Pre-Deployment**:

   - Verify environment configuration
   - Run pre-flight checks
   - Create database backup

2. **Database Migration**:

   - Run migration job
   - Verify migration success

3. **Service Deployment**:

   - Deploy or update services
   - Monitor rollout status
   - Verify service health

4. **Post-Deployment**:
   - Run smoke tests
   - Update documentation
   - Notify stakeholders

### Zero-Downtime Deployment Strategy

Implement zero-downtime deployments using Kubernetes:

1. **Rolling Updates**: Use Kubernetes rolling update strategy

   ```yaml
   spec:
     strategy:
       type: RollingUpdate
       rollingUpdate:
         maxSurge: 1
         maxUnavailable: 0
   ```

2. **Health Probes**: Configure proper readiness and liveness probes

   ```yaml
   readinessProbe:
     httpGet:
       path: /health/ready
       port: 8000
     initialDelaySeconds: 15
     periodSeconds: 10
   livenessProbe:
     httpGet:
       path: /health/live
       port: 8000
     initialDelaySeconds: 30
     periodSeconds: 20
   ```

3. **Connection Draining**: Ensure graceful termination of connections

   ```yaml
   # Define in deployment
   terminationGracePeriodSeconds: 60
   ```

4. **Versioned Endpoints**: Support multiple API versions during migration

## Rollback Procedures

### Automated Rollback Triggers

Define conditions that trigger automatic rollbacks:

1. **Health check failures**: Consecutive failed health checks
2. **Error rate thresholds**: Sudden increase in error rates
3. **Latency spikes**: Significant increase in response times
4. **Deployment timeouts**: Rollout exceeds expected duration

### Manual Rollback Procedure

```bash
# Rollback to previous version
kubectl rollout undo deployment/cortex-core-api -n cortex-core

# Rollback to specific version
kubectl rollout undo deployment/cortex-core-api -n cortex-core --to-revision=2

# Monitor rollback status
kubectl rollout status deployment/cortex-core-api -n cortex-core
```

### Database Rollback Strategy

1. **Schema versioning**: Keep schema changes backward compatible
2. **Rollback migrations**: Implement down migrations in Alembic
3. **Data backups**: Restore data from point-in-time backups if needed

```bash
# Roll back to previous migration
alembic downgrade -1

# Roll back to specific migration
alembic downgrade <migration_id>
```

## Backup and Recovery

### Database Backup Strategy

1. **Daily full backups**: Complete database dumps
2. **Continuous WAL archiving**: Transaction log backups
3. **Retention policy**: Keep daily backups for 7 days, weekly for 1 month, monthly for 1 year
4. **Encryption**: Encrypt all backup files

#### PostgreSQL Backup Script

```bash
#!/bin/bash
# backup-postgres.sh

# Variables
DB_HOST=${DB_HOST:-postgres}
DB_PORT=${DB_PORT:-5432}
DB_USER=${DB_USER:-postgres}
DB_PASSWORD=${DB_PASSWORD:-password}
DB_NAME=${DB_NAME:-cortex_core}
BACKUP_DIR=${BACKUP_DIR:-/var/backups/postgresql}
BACKUP_RETENTION=${BACKUP_RETENTION:-7}  # days

# Create backup directory
mkdir -p $BACKUP_DIR

# Generate timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup
PGPASSWORD=$DB_PASSWORD pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -F c -f $BACKUP_DIR/$DB_NAME-$TIMESTAMP.dump

# Encrypt backup
gpg --batch --yes --passphrase-file /etc/backup-passphrase --output $BACKUP_DIR/$DB_NAME-$TIMESTAMP.dump.gpg --symmetric $BACKUP_DIR/$DB_NAME-$TIMESTAMP.dump

# Remove unencrypted backup
rm $BACKUP_DIR/$DB_NAME-$TIMESTAMP.dump

# Delete old backups
find $BACKUP_DIR -name "$DB_NAME-*.dump.gpg" -type f -mtime +$BACKUP_RETENTION -delete

echo "Backup completed successfully: $BACKUP_DIR/$DB_NAME-$TIMESTAMP.dump.gpg"
```

### Recovery Procedures

#### Database Recovery

```bash
#!/bin/bash
# restore-postgres.sh

# Variables
DB_HOST=${DB_HOST:-postgres}
DB_PORT=${DB_PORT:-5432}
DB_USER=${DB_USER:-postgres}
DB_PASSWORD=${DB_PASSWORD:-password}
DB_NAME=${DB_NAME:-cortex_core}
BACKUP_FILE=${1:-""}

if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: restore-postgres.sh BACKUP_FILE"
  exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
  echo "Backup file not found: $BACKUP_FILE"
  exit 1
fi

# Decrypt backup if needed
if [[ "$BACKUP_FILE" == *.gpg ]]; then
  echo "Decrypting backup file..."
  DECRYPTED_FILE="${BACKUP_FILE%.gpg}"
  gpg --batch --yes --passphrase-file /etc/backup-passphrase --output $DECRYPTED_FILE --decrypt $BACKUP_FILE
  BACKUP_FILE=$DECRYPTED_FILE
fi

# Stop dependent services
echo "Stopping dependent services..."
kubectl scale deployment cortex-core-api --replicas=0 -n cortex-core

# Recreate database
echo "Recreating database..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -c "DROP DATABASE IF EXISTS $DB_NAME"
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -c "CREATE DATABASE $DB_NAME"

# Restore backup
echo "Restoring backup..."
PGPASSWORD=$DB_PASSWORD pg_restore -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -v $BACKUP_FILE

# Restart services
echo "Restarting services..."
kubectl scale deployment cortex-core-api --replicas=3 -n cortex-core

# Clean up decrypted file if it was created
if [[ "$BACKUP_FILE" == "${1%.gpg}" && "$BACKUP_FILE" != "$1" ]]; then
  rm $BACKUP_FILE
fi

echo "Recovery completed successfully"
```

### Disaster Recovery Plan

1. **Define recovery objectives**:

   - Recovery Time Objective (RTO): Maximum acceptable downtime
   - Recovery Point Objective (RPO): Maximum acceptable data loss

2. **Document recovery procedures**:

   - Infrastructure provisioning
   - Database restoration
   - Service deployment
   - Configuration restoration
   - Verification steps

3. **Regular testing**:
   - Schedule regular disaster recovery drills
   - Document and improve recovery procedures

## Scaling Strategy

### Horizontal Scaling

Scale services based on metrics:

```yaml
# horizontal-pod-autoscaler.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: cortex-core-api-hpa
  namespace: cortex-core
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: cortex-core-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
        - type: Percent
          value: 100
          periodSeconds: 60
        - type: Pods
          value: 4
          periodSeconds: 60
      selectPolicy: Max
```

### Database Scaling

#### Connection Pooling

Implement connection pooling to optimize database connections:

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os

# Create engine with connection pooling
engine = create_async_engine(
    os.getenv("DATABASE_URL"),
    echo=os.getenv("DB_ECHO", "false").lower() == "true",
    pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
    pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
    pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "1800"))
)

# Create session factory
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)
```

#### Database Replication

Set up read replicas for scaling read operations:

```yaml
# Example PostgreSQL read replica configuration
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres-core-replica
  namespace: cortex-core
spec:
  serviceName: postgres-core-replica
  replicas: 2
  selector:
    matchLabels:
      app: postgres-core-replica
  template:
    metadata:
      labels:
        app: postgres-core-replica
    spec:
      containers:
        - name: postgres
          image: postgres:14
          env:
            - name: POSTGRES_USER
              valueFrom:
                secretKeyRef:
                  name: postgres-credentials
                  key: username
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgres-credentials
                  key: password
            - name: POSTGRES_DB
              value: cortex_core
            - name: PGDATA
              value: /var/lib/postgresql/data/pgdata
            - name: PRIMARY_HOST
              value: postgres-core
            - name: PRIMARY_PORT
              value: "5432"
          command:
            - bash
            - -c
            - |
              echo "primary_conninfo = 'host=$PRIMARY_HOST port=$PRIMARY_PORT user=$POSTGRES_USER password=$POSTGRES_PASSWORD'" > /var/lib/postgresql/data/pgdata/recovery.conf
              echo "standby_mode = 'on'" >> /var/lib/postgresql/data/pgdata/recovery.conf
              postgres
          ports:
            - containerPort: 5432
          volumeMounts:
            - name: postgres-data
              mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
    - metadata:
        name: postgres-data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 100Gi
```

### Caching Strategy

Implement Redis for caching:

```yaml
# redis-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: cortex-core
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
        - name: redis
          image: redis:6-alpine
          ports:
            - containerPort: 6379
          resources:
            requests:
              memory: "256Mi"
              cpu: "100m"
            limits:
              memory: "512Mi"
              cpu: "200m"
          livenessProbe:
            tcpSocket:
              port: 6379
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            tcpSocket:
              port: 6379
            initialDelaySeconds: 5
            periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: cortex-core
spec:
  selector:
    app: redis
  ports:
    - port: 6379
      targetPort: 6379
```

Integrate Redis with FastAPI for caching:

```python
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
import redis
import os

# Initialize Redis connection
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    password=os.getenv("REDIS_PASSWORD", ""),
    db=int(os.getenv("REDIS_DB", "0")),
    decode_responses=True
)

# Initialize FastAPI cache
@app.on_event("startup")
async def startup():
    FastAPICache.init(
        RedisBackend(redis_client),
        prefix="cortex_cache:",
        expire=int(os.getenv("CACHE_EXPIRATION", "300"))
    )
```

## Infrastructure as Code

### Terraform Configuration

```hcl
# main.tf
provider "kubernetes" {
  config_path = "~/.kube/config"
  config_context = var.kubernetes_context
}

provider "helm" {
  kubernetes {
    config_path = "~/.kube/config"
    config_context = var.kubernetes_context
  }
}

resource "kubernetes_namespace" "cortex_core" {
  metadata {
    name = "cortex-core"
    labels = {
      name = "cortex-core"
    }
  }
}

resource "kubernetes_secret" "database_credentials" {
  metadata {
    name = "postgres-credentials"
    namespace = kubernetes_namespace.cortex_core.metadata[0].name
  }

  data = {
    username = var.db_username
    password = var.db_password
  }

  type = "Opaque"
}

resource "kubernetes_config_map" "cortex_core_config" {
  metadata {
    name = "cortex-core-config"
    namespace = kubernetes_namespace.cortex_core.metadata[0].name
  }

  data = {
    ENVIRONMENT = var.environment
    LOG_LEVEL = var.log_level
    REQUIRE_HTTPS = var.require_https
    ALLOWED_HOSTS = join(",", var.allowed_hosts)
    CORS_ORIGINS = join(",", var.cors_origins)
  }
}

resource "kubernetes_deployment" "cortex_core_api" {
  metadata {
    name = "cortex-core-api"
    namespace = kubernetes_namespace.cortex_core.metadata[0].name
    labels = {
      app = "cortex-core-api"
    }
  }

  spec {
    replicas = var.api_replicas

    selector {
      match_labels = {
        app = "cortex-core-api"
      }
    }

    template {
      metadata {
        labels = {
          app = "cortex-core-api"
        }
      }

      spec {
        container {
          image = "${var.container_registry}/cortex-core-api:${var.version}"
          name  = "cortex-core-api"

          port {
            container_port = 8000
          }

          env {
            name = "DATABASE_URL"
            value_from {
              secret_key_ref {
                name = kubernetes_secret.database_credentials.metadata[0].name
                key  = "database_url"
              }
            }
          }

          env_from {
            config_map_ref {
              name = kubernetes_config_map.cortex_core_config.metadata[0].name
            }
          }

          resources {
            limits = {
              cpu    = "2"
              memory = "4Gi"
            }
            requests = {
              cpu    = "1"
              memory = "2Gi"
            }
          }

          liveness_probe {
            http_get {
              path = "/health/live"
              port = 8000
            }
            initial_delay_seconds = 30
            period_seconds        = 20
          }

          readiness_probe {
            http_get {
              path = "/health/ready"
              port = 8000
            }
            initial_delay_seconds = 15
            period_seconds        = 10
          }
        }
      }
    }
  }
}

resource "kubernetes_service" "cortex_core_api" {
  metadata {
    name = "cortex-core-api"
    namespace = kubernetes_namespace.cortex_core.metadata[0].name
  }
  spec {
    selector = {
      app = kubernetes_deployment.cortex_core_api.metadata[0].labels.app
    }
    port {
      port        = 8000
      target_port = 8000
    }
    type = "ClusterIP"
  }
}

resource "kubernetes_ingress_v1" "cortex_core_ingress" {
  metadata {
    name = "cortex-core-ingress"
    namespace = kubernetes_namespace.cortex_core.metadata[0].name
    annotations = {
      "kubernetes.io/ingress.class" = "nginx"
      "nginx.ingress.kubernetes.io/ssl-redirect" = "true"
    }
  }

  spec {
    tls {
      hosts = [var.api_hostname]
      secret_name = "cortex-core-tls"
    }
    rule {
      host = var.api_hostname
      http {
        path {
          path = "/"
          path_type = "Prefix"
          backend {
            service {
              name = kubernetes_service.cortex_core_api.metadata[0].name
              port {
                number = 8000
              }
            }
          }
        }
      }
    }
  }
}
```

### Helm Charts

```yaml
# values.yaml
global:
  environment: production
  imageRegistry: registry.example.com
  version: 1.0.0

api:
  replicas: 3
  resources:
    requests:
      cpu: 1
      memory: 2Gi
    limits:
      cpu: 2
      memory: 4Gi
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 10
    targetCPUUtilizationPercentage: 70
    targetMemoryUtilizationPercentage: 80

memoryService:
  replicas: 3
  resources:
    requests:
      cpu: 1
      memory: 4Gi
    limits:
      cpu: 2
      memory: 8Gi

cognitionService:
  replicas: 3
  resources:
    requests:
      cpu: 2
      memory: 4Gi
    limits:
      cpu: 4
      memory: 8Gi

database:
  host: postgres-core
  port: 5432
  name: cortex_core
  username: cortex
  # password is provided via secrets

ingress:
  enabled: true
  hostname: api.cortex-core.example.com
  tls: true
  annotations:
    kubernetes.io/ingress.class: nginx
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
```

## Security Hardening

### TLS Configuration

Set up TLS for all services:

```yaml
# ingress-tls.yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: cortex-core-tls
  namespace: cortex-core
spec:
  secretName: cortex-core-tls
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  commonName: api.cortex-core.example.com
  dnsNames:
    - api.cortex-core.example.com
```

### Network Policies

Implement network policies to restrict traffic:

```yaml
# network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: cortex-core-api-policy
  namespace: cortex-core
spec:
  podSelector:
    matchLabels:
      app: cortex-core-api
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
      ports:
        - protocol: TCP
          port: 8000
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: memory-service
      ports:
        - protocol: TCP
          port: 9000
    - to:
        - podSelector:
            matchLabels:
              app: cognition-service
      ports:
        - protocol: TCP
          port: 9100
    - to:
        - podSelector:
            matchLabels:
              app: postgres-core
      ports:
        - protocol: TCP
          port: 5432
    - to:
        - namespaceSelector: {}
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
    - to:
        - ipBlock:
            cidr: 0.0.0.0/0
            except:
              - 10.0.0.0/8
              - 172.16.0.0/12
              - 192.168.0.0/16
      ports:
        - protocol: TCP
          port: 443
```

### Pod Security Context

Ensure pods run with restricted security contexts:

```yaml
spec:
  securityContext:
    runAsUser: 1000
    runAsGroup: 1000
    fsGroup: 1000
  containers:
    - name: cortex-core-api
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop:
            - ALL
```

### Resource Limits

Set appropriate resource limits for all containers:

```yaml
resources:
  requests:
    memory: "2Gi"
    cpu: "1"
  limits:
    memory: "4Gi"
    cpu: "2"
```

## Monitoring Integration

### Prometheus Integration

Set up service monitors for Prometheus:

```yaml
# service-monitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: cortex-core-monitor
  namespace: cortex-core
  labels:
    release: prometheus
spec:
  selector:
    matchLabels:
      app: cortex-core-api
  endpoints:
    - port: http
      path: /metrics
      interval: 15s
      scrapeTimeout: 10s
```

### Grafana Dashboard Provisioning

```yaml
# grafana-dashboard.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cortex-core-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  cortex-core-dashboard.json: |-
    {
      "annotations": {
        "list": []
      },
      "editable": true,
      "fiscalYearStartMonth": 0,
      "graphTooltip": 0,
      "id": null,
      "links": [],
      "liveNow": false,
      "panels": [
        {
          "datasource": {
            "type": "prometheus",
            "uid": "${DS_PROMETHEUS}"
          },
          "fieldConfig": {
            "defaults": {
              "color": {
                "mode": "palette-classic"
              },
              "custom": {
                "axisCenteredZero": false,
                "axisColorMode": "text",
                "axisLabel": "",
                "axisPlacement": "auto",
                "barAlignment": 0,
                "drawStyle": "line",
                "fillOpacity": 10,
                "gradientMode": "none",
                "hideFrom": {
                  "legend": false,
                  "tooltip": false,
                  "viz": false
                },
                "insertNulls": false,
                "lineInterpolation": "linear",
                "lineWidth": 1,
                "pointSize": 5,
                "scaleDistribution": {
                  "type": "linear"
                },
                "showPoints": "auto",
                "spanNulls": false,
                "stacking": {
                  "group": "A",
                  "mode": "none"
                },
                "thresholdsStyle": {
                  "mode": "off"
                }
              },
              "mappings": [],
              "thresholds": {
                "mode": "absolute",
                "steps": [
                  {
                    "color": "green",
                    "value": null
                  },
                  {
                    "color": "red",
                    "value": 80
                  }
                ]
              },
              "unit": "short"
            },
            "overrides": []
          },
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 0,
            "y": 0
          },
          "id": 1,
          "options": {
            "legend": {
              "calcs": [],
              "displayMode": "list",
              "placement": "bottom",
              "showLegend": true
            },
            "tooltip": {
              "mode": "single",
              "sort": "none"
            }
          },
          "targets": [
            {
              "datasource": {
                "type": "prometheus",
                "uid": "${DS_PROMETHEUS}"
              },
              "expr": "sum(rate(http_requests_total{namespace=\"cortex-core\"}[5m])) by (pod)",
              "refId": "A"
            }
          ],
          "title": "HTTP Request Rate",
          "type": "timeseries"
        }
      ],
      "refresh": "",
      "schemaVersion": 38,
      "style": "dark",
      "tags": [],
      "templating": {
        "list": []
      },
      "time": {
        "from": "now-6h",
        "to": "now"
      },
      "timepicker": {},
      "timezone": "",
      "title": "Cortex Core Dashboard",
      "version": 0,
      "weekStart": ""
    }
```

## Conclusion

This production deployment guide provides comprehensive instructions for deploying the Cortex Core platform to production environments. It covers all aspects of deployment, including containerization, Kubernetes configuration, environment management, secrets handling, database initialization, deployment workflows, and security hardening.

By following these guidelines, a mid-level engineer can successfully deploy the Cortex Core platform with enterprise-grade features, ensuring reliability, security, and scalability in production environments.

The deployment process is designed for zero-downtime updates, with proper rollback procedures and disaster recovery planning. The infrastructure as code approach ensures reproducible deployments across environments, while the comprehensive monitoring and alerting provide visibility into system health and performance.

### Next Steps

After deploying to production, consider these follow-up activities:

1. **Performance tuning**: Analyze real-world usage patterns and optimize accordingly
2. **Load testing**: Verify system performance under expected and peak loads
3. **Security auditing**: Conduct regular security assessments
4. **Disaster recovery drills**: Practice recovery procedures regularly
5. **Documentation updates**: Keep deployment documentation current with any changes
6. **Monitoring refinement**: Adjust alerts and dashboards based on operational experience
