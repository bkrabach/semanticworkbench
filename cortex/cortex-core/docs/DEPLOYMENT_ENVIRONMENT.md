# Cortex Core Deployment and Environment Setup

## Overview

This document provides instructions for deploying the Cortex Core MVP and its associated backend stub services (Memory Service and Cognition Service) in a local development environment. It also outlines considerations for production deployment using Azure App Service and PostgreSQL. Included are details on environment variables, Docker Compose setup, and CI/CD considerations.

## Local Development Setup

### Prerequisites

- Python 3.10 or higher
- Docker and Docker Compose installed
- Git installed

### Environment Variables

Create a `.env` file in the project root to configure necessary environment variables. For example:

```env
# For Cortex Core
ENV=development
DEBUG=True

# Authentication (stub for now)
B2C_TENANT_ID=dummy-tenant
B2C_CLIENT_ID=dummy-client-id
B2C_CLIENT_SECRET=dummy-client-secret

# Database configuration (using SQLite for development)
DATABASE_URL=sqlite:///./cortex_core.db

# Endpoints for backend stubs
MEMORY_SERVICE_URL=http://localhost:9000
COGNITION_SERVICE_URL=http://localhost:9100
```

### Docker Compose Setup

The sample `docker-compose.yml` below brings up the Cortex Core and backend stub services together:

```yaml
version: "3.8"
services:
  cortex-core:
    build:
      context: ./cortex-core
    image: cortex-core:latest
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      - memory-service
      - cognition-service

  memory-service:
    build:
      context: ./memory-service
    image: memory-service:latest
    ports:
      - "9000:9000"
    env_file: .env

  cognition-service:
    build:
      context: ./cognition-service
    image: cognition-service:latest
    ports:
      - "9100:9100"
    env_file: .env
```

### Running Locally with Docker Compose

1. Build and start the services by running from the project root:

   ```bash
   docker-compose up --build
   ```

2. The Cortex Core will run on port 8000, the Memory Service Stub on port 9000, and the Cognition Service Stub on port 9100.

### Running Services Without Docker

Alternatively, you can run each service using `uvicorn`:

- **Cortex Core:**

  ```bash
  uvicorn cortex_core:app --host 0.0.0.0 --port 8000 --reload
  ```

- **Memory Service:**

  ```bash
  uvicorn memory_stub:app --host 0.0.0.0 --port 9000 --reload
  ```

- **Cognition Service:**

  ```bash
  uvicorn cognition_stub:app --host 0.0.0.0 --port 9100 --reload
  ```

## CI/CD Considerations

- **GitHub Actions:**
  Set up CI workflows using GitHub Actions to:

  - Create a virtual environment.
  - Install dependencies.
  - Run linting (using tools such as Ruff and Black).
  - Execute the integration test suite with `pytest`.

- **Azure App Service Deployment:**
  For production deployment:

  - Use Azure Container Registry (ACR) to host the Docker images.
  - Configure environment variables in the Azure portal.
  - Set up a CI/CD pipeline that builds, pushes images to ACR, and deploys to Azure App Service.

- **Database Migrations:**
  Use Alembic to manage migrations when transitioning from SQLite (development) to PostgreSQL (production).

## Summary

This document outlines step-by-step instructions for deploying the Cortex Core MVP in a local environment using Docker Compose, details for running services individually, and guidance on CI/CD and production deployment setups. This should help your team set up a reliable development environment and prepare for future production deployments.
