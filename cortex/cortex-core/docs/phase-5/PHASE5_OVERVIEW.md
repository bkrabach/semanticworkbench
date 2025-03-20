# Cortex Core Phase 5: Production Hardening

## Project Overview

Phase 5 completes the production-ready implementation of the Cortex Core platform by focusing on enterprise authentication, robust persistence, comprehensive error handling, logging, monitoring, performance optimization, security hardening, and thorough documentation. Building on the distributed architecture established in Phase 4, this phase ensures the system is ready for production deployment with enterprise-grade features and practices.

This final phase enhances the system by integrating with Azure B2C for authentication, migrating to PostgreSQL for production-grade persistence, implementing comprehensive error handling and logging, optimizing performance, hardening security, and creating complete documentation for all aspects of the system.

## Goals of Phase 5

1. **Implement Azure B2C Integration**: Replace the simplified JWT authentication with enterprise-grade Azure B2C
2. **Migrate to PostgreSQL**: Replace SQLite with PostgreSQL for production-grade persistence
3. **Enhance Error Handling**: Implement comprehensive error handling across all components
4. **Add Logging and Monitoring**: Create production-ready logging and monitoring infrastructure
5. **Optimize Performance**: Identify and resolve performance bottlenecks
6. **Harden Security**: Implement security best practices across the system
7. **Create Comprehensive Documentation**: Document all aspects of the system for users, administrators, and developers
8. **Ensure Production Readiness**: Validate the system against production-readiness criteria

## System Architecture - Phase 5

```mermaid
graph TD
    Client1[Input Client] -->|POST /input| API[FastAPI Application]
    Client2[Output Client] -->|GET /output/stream| API
    Client3[Config Client] -->|POST,GET /config/*| API

    API --> AzureB2C[Azure B2C Authentication]
    API --> InputAPI[Input API]
    API --> OutputAPI[Output API]
    API --> ConfigAPI[Configuration API]

    InputAPI --> NetworkMcpClient[Network MCP Client]
    OutputAPI --> EventBus[Event Bus]
    ConfigAPI --> Repositories[Repository Layer]

    NetworkMcpClient -->|HTTP/SSE| ServiceDiscovery[Service Discovery]
    EventBus --> NetworkMcpClient

    ServiceDiscovery -->|Resolve| MemoryService[Memory Service]
    ServiceDiscovery -->|Resolve| CognitionService[Cognition Service]

    MemoryService -->|HTTP/SSE| CognitionService
    MemoryService --> MemoryDB[(Memory PostgreSQL)]

    Repositories --> CoreDB[(Core PostgreSQL)]

    Monitoring[Logging & Monitoring] -.-> API
    Monitoring -.-> MemoryService
    Monitoring -.-> CognitionService

    subgraph "Production Components"
        AzureB2C
        CoreDB
        MemoryDB
        Monitoring
    end

    subgraph "Security Components"
        HTTPS[HTTPS Enforcement]
        RateLimiting[Rate Limiting]
        SecureHeaders[Secure Headers]
    end

    HTTPS -.-> API
    RateLimiting -.-> API
    SecureHeaders -.-> API

    style API stroke:#f9f,stroke-width:4
    style EventBus stroke:#bbf,stroke-width:4
    style CoreDB stroke:#bfb,stroke-width:4
    style AzureB2C stroke:#fbb,stroke-width:4
    style NetworkMcpClient stroke:#9bf,stroke-width:4
    style MemoryService stroke:#f9b,stroke-width:4
    style CognitionService stroke:#9fb,stroke-width:4
    style Monitoring stroke:#ff9,stroke-width:4
```

### Phase 5 Components

1. **Azure B2C Integration** (New)

   - Enterprise-grade authentication
   - Single sign-on capabilities
   - User profile management
   - Role-based access control
   - Token validation with B2C keys
   - JWT token handling with B2C claims

2. **PostgreSQL Database** (New)

   - Production-grade persistence
   - Schema migration from SQLite
   - Connection pooling
   - Transaction management
   - Database optimization
   - Backup and recovery procedures

3. **Comprehensive Error Handling** (Enhanced)

   - Global error handler
   - Structured error logging
   - Client-friendly error messages
   - Error categorization
   - Correlation IDs for tracking
   - Error reporting and monitoring

4. **Logging and Monitoring** (New)

   - Structured logging
   - Log aggregation
   - Metrics collection
   - Health check endpoints
   - Performance monitoring
   - Alert configuration

5. **Security Components** (Enhanced)

   - HTTPS enforcement
   - API rate limiting
   - Secure header configuration
   - Input validation
   - Database security hardening
   - Authentication security

6. **Performance Optimization** (Enhanced)

   - Database query optimization
   - Connection pooling tuning
   - Caching implementation
   - Resource utilization improvements
   - Network communication efficiency
   - Memory usage optimization

7. **Comprehensive Documentation** (New)
   - API documentation with OpenAPI
   - Architecture documentation
   - User guides
   - Administrator documentation
   - Developer guides
   - Troubleshooting information

## What's Included in Phase 5

- ✅ Complete Azure B2C integration
- ✅ PostgreSQL migration for all databases
- ✅ Comprehensive error handling framework
- ✅ Structured logging implementation
- ✅ Monitoring and metrics collection
- ✅ Performance optimization
- ✅ Security hardening across all components
- ✅ HTTPS enforcement
- ✅ API rate limiting
- ✅ Input validation improvements
- ✅ Database connection pooling and optimization
- ✅ Caching strategies for appropriate data
- ✅ Complete OpenAPI documentation
- ✅ User, administrator, and developer guides
- ✅ Production deployment documentation
- ✅ Backup and recovery procedures

## What's Explicitly NOT Included in Phase 5

- ❌ Complex microservice orchestration
- ❌ Multi-region deployment
- ❌ Advanced analytics and reporting
- ❌ Complex permissioning systems
- ❌ Custom B2C policy development
- ❌ Sophisticated caching infrastructure
- ❌ Complex CI/CD pipelines
- ❌ Advanced multi-tenancy
- ❌ Third-party integrations not specified
- ❌ Complex scaling rules
- ❌ Feature development beyond hardening

## Success Criteria for Phase 5

Phase 5 is considered successfully completed when:

1. Users can authenticate using Azure B2C
2. All data is stored in PostgreSQL databases
3. The system handles errors gracefully across all components
4. Logging provides comprehensive visibility into system operations
5. Monitoring shows system health and performance
6. Security meets enterprise standards
7. Performance is optimized for production workloads
8. Documentation is complete and usable
9. The system meets all production-readiness criteria
10. Existing functionality continues to work with enhanced components

## Key Implementation Principles for Phase 5

1. **Enterprise Integration**: Properly integrate with enterprise systems like Azure B2C
2. **Production-Ready Database**: Implement PostgreSQL with proper setup and configuration
3. **Comprehensive Error Handling**: Ensure all errors are properly caught, logged, and reported
4. **Structured Logging**: Implement consistent, structured logging across all components
5. **Performance Focus**: Optimize performance in targeted areas without premature optimization
6. **Security First**: Apply security best practices consistently across the system
7. **Documentation Completeness**: Ensure documentation covers all aspects of the system
8. **User-Centric Design**: Keep user experience in mind for error messages and documentation
9. **Operational Excellence**: Design for operations with monitoring, alerting, and troubleshooting
10. **Simplified Production Readiness**: Focus on essential production requirements without unnecessary complexity

## Phase 5 Data Flow

1. **Authentication Flow with Azure B2C**:

   ```
   Client → Azure B2C Login → Azure B2C → JWT Token →
   Client → API Request + JWT → API →
   B2C Token Validation → Request Processing
   ```

2. **Input Processing Flow with PostgreSQL**:

   ```
   Client → POST /input + JWT → Input API → Network MCP Client →
   Memory Service Tool:store_input →
   Connection Pool → PostgreSQL Database → Response
   ```

3. **Error Handling Flow**:
   ```
   API Error → Global Error Handler → Error Logging →
   Correlation ID Generation → Structured Error Response →
   Client Feedback → Monitoring Alert (if needed)
   ```

## Critical Implementation Details

### Azure B2C Integration

Azure B2C provides enterprise-grade authentication and user management for the Cortex Core system.

Key details:

- B2C tenant configuration
- JWT token validation with B2C keys
- User profile and claims mapping
- Role-based access control
- Single sign-on capabilities
- B2C policy configuration

**Azure B2C Integration Example**:

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2AuthorizationCodeBearer
import requests
from jose import jwt, JWTError
from app.config import settings

# OAuth2 scheme for B2C
oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"https://{settings.B2C_TENANT}.b2clogin.com/{settings.B2C_TENANT}.onmicrosoft.com/{settings.B2C_POLICY}/oauth2/v2.0/authorize",
    tokenUrl=f"https://{settings.B2C_TENANT}.b2clogin.com/{settings.B2C_TENANT}.onmicrosoft.com/{settings.B2C_POLICY}/oauth2/v2.0/token",
    scopes={"user.read": "Read user profile"}
)

# Cache for OpenID configuration
OPENID_CONFIG = None
JWKS = None

async def get_openid_config():
    """Get OpenID configuration from Azure B2C"""
    global OPENID_CONFIG

    if OPENID_CONFIG is None:
        url = f"https://{settings.B2C_TENANT}.b2clogin.com/{settings.B2C_TENANT}.onmicrosoft.com/{settings.B2C_POLICY}/v2.0/.well-known/openid-configuration"
        response = requests.get(url)
        response.raise_for_status()
        OPENID_CONFIG = response.json()

    return OPENID_CONFIG

async def get_jwks():
    """Get JSON Web Key Set from Azure B2C"""
    global JWKS

    if JWKS is None:
        config = await get_openid_config()
        jwks_uri = config["jwks_uri"]
        response = requests.get(jwks_uri)
        response.raise_for_status()
        JWKS = response.json()

    return JWKS

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Validate B2C JWT token and extract user information"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Get JWKs for token validation
        jwks = await get_jwks()

        # Decode and validate token
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            audience=settings.B2C_CLIENT_ID,
            issuer=f"https://{settings.B2C_TENANT}.b2clogin.com/{settings.B2C_TENANT}.onmicrosoft.com/v2.0/"
        )

        # Extract user information
        user_id = payload.get("oid")
        name = payload.get("name")
        email = payload.get("emails")[0] if "emails" in payload and payload["emails"] else payload.get("email")

        if user_id is None:
            raise credentials_exception

        # Create user context
        user = {
            "user_id": user_id,
            "name": name,
            "email": email,
            "roles": payload.get("roles", [])
        }

        return user

    except JWTError:
        raise credentials_exception
```

### PostgreSQL Migration

PostgreSQL provides a production-grade database solution with better performance, reliability, and scalability than SQLite.

Key details:

- Schema migration from SQLite
- Connection pooling for efficiency
- Transaction management
- Database optimization
- PostgreSQL-specific features
- Backup and recovery procedures

**PostgreSQL Connection Example**:

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE
)

# Create async session factory
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db():
    """Get database session"""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

**Migration Script Example**:

```python
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '1a2b3c4d5e6f'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create users table
    op.create_table(
        'users',
        sa.Column('user_id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}')
    )

    # Create workspaces table
    op.create_table(
        'workspaces',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('owner_id', sa.String(36), sa.ForeignKey('users.user_id'), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now())
    )

    # Create index on owner_id
    op.create_index('ix_workspaces_owner_id', 'workspaces', ['owner_id'])

    # Add more tables and indexes...
```

### Comprehensive Error Handling

A robust error handling framework ensures that all errors are properly caught, logged, and reported to users.

Key details:

- Global error handler
- Structured error logging
- Correlation IDs for tracking
- User-friendly error messages
- Error categorization
- Integration with monitoring

**Global Error Handler Example**:

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uuid
import logging
from app.utils.logger import get_logger

logger = get_logger(__name__)

app = FastAPI()

class AppException(Exception):
    """Base exception for application errors"""
    def __init__(self, status_code: int, code: str, message: str, details: dict = None):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)

@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    """Add correlation ID to request and response"""
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    request.state.correlation_id = correlation_id

    try:
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
    except Exception as e:
        logger.exception(f"Unhandled exception: {str(e)}", extra={"correlation_id": correlation_id})
        return await handle_exception(request, e)

async def handle_exception(request: Request, exc: Exception):
    """Handle exceptions and return appropriate response"""
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))

    if isinstance(exc, AppException):
        # Handle known application exceptions
        content = {
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "correlation_id": correlation_id
            }
        }
        return JSONResponse(status_code=exc.status_code, content=content)
    else:
        # Handle unexpected exceptions
        content = {
            "error": {
                "code": "internal_error",
                "message": "An unexpected error occurred",
                "correlation_id": correlation_id
            }
        }

        if app.debug:
            # Include exception details in debug mode
            content["error"]["details"] = {
                "exception": str(exc),
                "type": exc.__class__.__name__
            }

        return JSONResponse(status_code=500, content=content)

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Handle application exceptions"""
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))

    logger.error(
        f"Application exception: {exc.code} - {exc.message}",
        extra={
            "correlation_id": correlation_id,
            "exception_code": exc.code,
            "exception_details": exc.details
        }
    )

    content = {
        "error": {
            "code": exc.code,
            "message": exc.message,
            "details": exc.details,
            "correlation_id": correlation_id
        }
    }

    return JSONResponse(status_code=exc.status_code, content=content)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    return await handle_exception(request, exc)
```

### Structured Logging

Consistent, structured logging across all components provides essential visibility into system operations.

Key details:

- Structured log format (JSON)
- Contextual information
- Log level configuration
- Performance metrics
- Integration with log aggregation
- Request/response logging

**Structured Logger Example**:

```python
import logging
import json
import os
from datetime import datetime
import uuid

class StructuredLogFormatter(logging.Formatter):
    """Formatter for structured JSON logs"""

    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process_id": os.getpid()
        }

        # Add correlation ID if available
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id

        # Add exception info if available
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add any extra attributes
        for key, value in record.__dict__.items():
            if key not in ["args", "asctime", "created", "exc_info", "exc_text", "filename",
                          "funcName", "id", "levelname", "levelno", "lineno", "module",
                          "msecs", "message", "msg", "name", "pathname", "process",
                          "processName", "relativeCreated", "stack_info", "thread", "threadName",
                          "correlation_id"]:
                log_data[key] = value

        return json.dumps(log_data)

def setup_logging():
    """Configure structured logging"""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Remove existing handlers
    for handler in root_logger.handlers:
        root_logger.removeHandler(handler)

    # Create console handler with structured formatter
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(StructuredLogFormatter())
    root_logger.addHandler(console_handler)

    # Set specific levels for verbose loggers
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)

    return root_logger

def get_logger(name):
    """Get a logger with the given name"""
    return logging.getLogger(name)

class LoggingMiddleware:
    """Middleware for logging requests and responses"""

    async def __call__(self, request, call_next):
        # Generate correlation ID if not present
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))

        # Get logger
        logger = get_logger("api.request")

        # Log request
        logger.info(
            f"Request: {request.method} {request.url.path}",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_ip": request.client.host,
                "user_agent": request.headers.get("User-Agent")
            }
        )

        # Process request
        start_time = datetime.utcnow()
        response = await call_next(request)
        process_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        # Log response
        logger.info(
            f"Response: {response.status_code} ({process_time:.2f}ms)",
            extra={
                "correlation_id": correlation_id,
                "status_code": response.status_code,
                "process_time_ms": process_time
            }
        )

        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id

        return response
```

### Security Hardening

Security best practices are applied consistently across the system to ensure enterprise-grade protection.

Key details:

- HTTPS enforcement
- Secure header configuration
- API rate limiting
- Input validation
- Database security
- Authentication security
- Secrets management

**Security Middleware Example**:

```python
from fastapi import FastAPI, Request, Response
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from app.config import settings

app = FastAPI()

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.middleware("http")
async def secure_headers_middleware(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)

    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), interest-cohort=()"

    return response

@app.middleware("http")
async def https_redirect_middleware(request: Request, call_next):
    """Redirect HTTP requests to HTTPS"""
    if settings.REQUIRE_HTTPS and request.url.scheme == "http":
        url = request.url.replace(scheme="https")
        return Response(status_code=301, headers={"Location": str(url)})

    return await call_next(request)
```

### Performance Optimization

Targeted performance improvements ensure the system can handle production workloads efficiently.

Key details:

- Database query optimization
- Connection pooling tuning
- Caching implementation
- Resource utilization improvements
- Network communication efficiency
- Memory usage optimization

**Caching Implementation Example**:

```python
from fastapi import Depends, HTTPException
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache
import redis
import json
from app.config import settings
from app.database.models import Workspace

# Initialize Redis connection
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    db=settings.REDIS_DB,
    decode_responses=True
)

def setup_cache():
    """Initialize cache backend"""
    FastAPICache.init(
        RedisBackend(redis_client),
        prefix="cortex_cache:",
        expire=settings.CACHE_EXPIRATION
    )

# Cache workspace retrieval
@cache(expire=300)
async def get_workspace_cached(workspace_id: str, owner_id: str):
    """Get workspace with caching"""
    # Implementation to get workspace from database
    workspace = await get_workspace_from_db(workspace_id, owner_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace

# Database query optimization example
async def get_conversations_optimized(workspace_id: str, limit: int = 100, offset: int = 0):
    """Optimized query for conversations"""
    query = """
    SELECT
        c.id,
        c.topic,
        c.metadata,
        c.created_at,
        COUNT(m.id) AS message_count,
        MAX(m.timestamp) AS last_activity
    FROM
        conversations c
    LEFT JOIN
        messages m ON c.id = m.conversation_id
    WHERE
        c.workspace_id = :workspace_id
    GROUP BY
        c.id
    ORDER BY
        last_activity DESC
    LIMIT
        :limit
    OFFSET
        :offset
    """

    result = await db.execute(
        query,
        {"workspace_id": workspace_id, "limit": limit, "offset": offset}
    )

    return result.mappings().all()
```

### Comprehensive Documentation

Complete documentation covers all aspects of the system for users, administrators, and developers.

Key details:

- API documentation with OpenAPI
- Architecture documentation
- User guides
- Administrator documentation
- Developer guides
- Troubleshooting information
- Deployment guides

**OpenAPI Enhancement Example**:

```python
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

app = FastAPI(
    title="Cortex Core API",
    description="Enterprise API for the Cortex Core platform",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

def custom_openapi():
    """Generate custom OpenAPI schema"""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Cortex Core API",
        version="1.0.0",
        description="Enterprise API for the Cortex Core platform",
        routes=app.routes,
    )

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "OAuth2": {
            "type": "oauth2",
            "flows": {
                "authorizationCode": {
                    "authorizationUrl": f"https://{settings.B2C_TENANT}.b2clogin.com/{settings.B2C_TENANT}.onmicrosoft.com/{settings.B2C_POLICY}/oauth2/v2.0/authorize",
                    "tokenUrl": f"https://{settings.B2C_TENANT}.b2clogin.com/{settings.B2C_TENANT}.onmicrosoft.com/{settings.B2C_POLICY}/oauth2/v2.0/token",
                    "scopes": {
                        "user.read": "Read user profile",
                        "api.access": "Access Cortex Core API"
                    }
                }
            }
        }
    }

    # Add security requirement
    openapi_schema["security"] = [{"OAuth2": ["api.access"]}]

    # Add additional OpenAPI information
    openapi_schema["info"]["contact"] = {
        "name": "Cortex Support",
        "url": "https://example.com/support",
        "email": "support@example.com"
    }

    openapi_schema["info"]["license"] = {
        "name": "Proprietary",
        "url": "https://example.com/license"
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

## Integration with Client Applications

Phase 5 maintains compatibility with client applications while enhancing the underlying system.

### For Client Developers

1. **Azure B2C Authentication**:

   - Authenticate using Azure B2C login flow
   - Obtain JWT token from B2C
   - Include token in Authorization header
   - Handle token refresh
   - Process B2C-specific claims

2. **Error Handling Improvements**:

   - Process structured error responses
   - Use correlation IDs for troubleshooting
   - Handle specific error codes appropriately
   - Implement retry logic for transient errors
   - Display user-friendly error messages

3. **Performance Considerations**:

   - Leverage caching where appropriate
   - Minimize request payload size
   - Follow rate limiting guidelines
   - Implement connection pooling
   - Use compression for large responses

4. **Security Enhancements**:
   - Ensure HTTPS for all communication
   - Implement proper token storage
   - Validate user input before sending
   - Follow content security policy
   - Implement proper logout procedures

## Common Pitfalls and Challenges

Be aware of these common implementation challenges specific to Phase 5:

1. **Azure B2C Integration Issues**:

   - Incorrect B2C policy configuration
   - Missing or incorrect token validation
   - Improper claims mapping
   - Poor error handling for authentication failures
   - Inadequate role-based access control

2. **PostgreSQL Migration Challenges**:

   - Schema compatibility issues
   - Performance regression after migration
   - Connection pool exhaustion
   - Transaction isolation problems
   - Backup and recovery process issues

3. **Monitoring and Logging Mistakes**:

   - Excessive logging causing performance issues
   - Missing critical log information
   - Poor log structure for analysis
   - Inadequate monitoring coverage
   - Alert fatigue from too many notifications

4. **Security Implementation Issues**:

   - Incomplete HTTPS enforcement
   - Missing input validation
   - Inadequate rate limiting
   - Security headers not applied consistently
   - Improper secrets management

5. **Performance Optimization Challenges**:
   - Premature optimization
   - Caching invalidation issues
   - Database query complexity
   - Memory leaks in long-running processes
   - Connection management issues

## Validating Your Implementation

To ensure your Phase 5 implementation is correct:

1. **Authentication Testing**:

   - Test Azure B2C login flow
   - Verify token validation
   - Test role-based access control
   - Verify token refresh
   - Test authentication error scenarios

2. **Database Migration Testing**:

   - Verify data integrity after migration
   - Test query performance
   - Validate connection pooling
   - Test transaction handling
   - Verify backup and recovery procedures

3. **Security Assessment**:

   - Perform security scanning
   - Test HTTPS enforcement
   - Verify secure headers
   - Test rate limiting effectiveness
   - Validate input validation

4. **Performance Testing**:

   - Conduct load testing
   - Measure response times
   - Test caching effectiveness
   - Verify resource utilization
   - Test scaling behavior

5. **Documentation Verification**:
   - Validate API documentation accuracy
   - Test example code snippets
   - Review user guide clarity
   - Verify administrator documentation
   - Test troubleshooting procedures

## Phase 5 in the Overall Project Timeline

Phase 5 completes the phased development approach:

1. Phase 1: Functional Input/Output System with In-Memory Storage
2. Phase 2: Configuration API & Basic Persistence
3. Phase 3: MCP Protocol and Service Architecture
4. Phase 4: Distributed Services
5. **Phase 5: Production Hardening** (current phase)

## Developer Environment

Phase 5 requires the following additions to the Phase 4 environment:

- Azure B2C application registration
- PostgreSQL database
- Redis (for caching)
- Enhanced logging tools
- Security scanning tools
- Performance testing tools

Additional environment variables:

```
# Azure B2C configuration
B2C_TENANT=your-tenant
B2C_CLIENT_ID=your-client-id
B2C_CLIENT_SECRET=your-client-secret
B2C_POLICY=B2C_1_SignUpSignIn

# PostgreSQL configuration
DATABASE_URL=postgresql+asyncpg://user:password@host:port/dbname
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800

# Redis configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your-password
REDIS_DB=0
CACHE_EXPIRATION=300

# Security configuration
REQUIRE_HTTPS=true
ALLOWED_HOSTS=["example.com", "api.example.com"]
CORS_ORIGINS=["https://example.com"]
```

## Implementation Approach

The recommended implementation sequence for Phase 5 is:

1. **PostgreSQL Migration**

   - Set up PostgreSQL database
   - Create migration scripts
   - Implement connection pooling
   - Migrate data from SQLite
   - Test database performance
   - Implement backup procedures

2. **Azure B2C Integration**

   - Register application in Azure B2C
   - Configure B2C policies
   - Implement token validation
   - Update authentication middleware
   - Map B2C claims to user context
   - Test authentication flow

3. **Error Handling Framework**

   - Implement global error handler
   - Create structured error logging
   - Add correlation ID tracking
   - Define error response format
   - Implement error categorization
   - Test error scenarios

4. **Logging and Monitoring**

   - Implement structured logging
   - Add request/response logging
   - Create health check endpoints
   - Set up metric collection
   - Configure alerting
   - Test monitoring scenarios

5. **Security Hardening**

   - Enforce HTTPS
   - Implement secure headers
   - Add API rate limiting
   - Enhance input validation
   - Secure database access
   - Implement secrets management
   - Perform security scanning

6. **Performance Optimization**

   - Identify performance bottlenecks
   - Optimize database queries
   - Implement caching
   - Tune connection pooling
   - Optimize resource usage
   - Conduct load testing

7. **Documentation**

   - Create OpenAPI documentation
   - Write user guides
   - Create administrator documentation
   - Document deployment procedures
   - Create troubleshooting guides
   - Document architecture

8. **Production Readiness Verification**
   - Create production readiness checklist
   - Conduct comprehensive testing
   - Perform security assessment
   - Validate performance targets
   - Verify documentation completeness
   - Test backup and recovery procedures

At each step, verify that the implementation meets production requirements before moving on.

## Conclusion

Phase 5 completes the Cortex Core platform by implementing production-grade features and practices. By integrating with Azure B2C, migrating to PostgreSQL, enhancing error handling and logging, optimizing performance, hardening security, and creating comprehensive documentation, this phase ensures the system is enterprise-ready.

The focus remains on pragmatic implementation and essential production requirements, avoiding unnecessary complexity while ensuring the system meets enterprise standards. This approach results in a robust, scalable platform that can be confidently deployed to production environments.

The implementation of Phase 5 marks the completion of the phased development approach, delivering a fully-functional, production-ready Cortex Core platform that meets the needs of both users and administrators.
