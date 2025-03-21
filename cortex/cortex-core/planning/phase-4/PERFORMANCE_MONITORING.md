# Performance Monitoring Guide for Cortex Core Phase 4

## Overview

This document provides a comprehensive guide to monitoring and performance considerations for the distributed Cortex Core system in Phase 4. It covers key performance metrics, instrumentation approaches, monitoring tools, resource utilization guidelines, bottleneck identification, and performance optimization techniques.

In Phase 4, monitoring becomes significantly more important as services move from in-process to distributed deployments. This guide focuses on practical, lightweight approaches to monitoring that provide valuable insights without introducing excessive overhead or complexity, following the project's philosophy of ruthless simplicity.

## Key Performance Metrics

### Core Service Metrics

Each service in the Cortex Core system should track the following fundamental metrics:

#### 1. Request-Level Metrics

| Metric                  | Description                                       | Importance                                           |
| ----------------------- | ------------------------------------------------- | ---------------------------------------------------- |
| Request Rate            | Requests per second handled by the service        | High - Indicates load and traffic patterns           |
| Latency (p50, p95, p99) | Time to process requests at different percentiles | High - Identifies performance issues affecting users |
| Error Rate              | Percentage of requests that result in errors      | High - Indicates system health and reliability       |
| Success Rate            | Percentage of requests that succeed               | High - Overall system quality indicator              |

#### 2. Resource Utilization Metrics

| Metric           | Description                       | Importance                                         |
| ---------------- | --------------------------------- | -------------------------------------------------- |
| CPU Usage        | Percentage of CPU utilized        | Medium - Identifies compute bottlenecks            |
| Memory Usage     | Memory consumption                | Medium - Identifies memory leaks and sizing issues |
| Network I/O      | Network traffic in/out            | Medium - Identifies communication bottlenecks      |
| Disk I/O         | Disk operations per second        | Low/Medium - Important for database services       |
| Connection Count | Active connections to the service | Medium - Identifies connection management issues   |

#### 3. Application-Specific Metrics

| Metric                | Description                                 | Importance                                         |
| --------------------- | ------------------------------------------- | -------------------------------------------------- |
| Queue Length          | Items waiting to be processed               | High - Indicates backpressure or processing issues |
| Active Workers        | Number of active processing threads/workers | Medium - Shows parallelism effectiveness           |
| Cache Hit Rate        | Percentage of lookups satisfied from cache  | Medium - Effectiveness of caching strategies       |
| Background Task Count | Number of background tasks                  | Medium - Indicates asynchronous processing load    |

### Service-Specific Metrics

#### Core API Service Metrics

| Metric                  | Description                                 | Target                            |
| ----------------------- | ------------------------------------------- | --------------------------------- |
| Input Request Rate      | Rate of incoming requests                   | Depends on expected load          |
| SSE Connection Count    | Number of active SSE connections            | Monitor for unexpected growth     |
| Event Bus Queue Size    | Size of event bus message queues            | Should remain low (<100)          |
| Event Delivery Latency  | Time from event creation to client delivery | <500ms for interactive experience |
| MCP Client Request Rate | Requests to backend services                | Track for capacity planning       |
| Authentication Latency  | Time to validate JWT tokens                 | <50ms                             |

#### Memory Service Metrics

| Metric                    | Description                         | Target                               |
| ------------------------- | ----------------------------------- | ------------------------------------ |
| Storage Operation Rate    | Rate of read/write operations       | Depends on expected load             |
| Storage Operation Latency | Time to complete storage operations | <100ms                               |
| Database Size             | Total size of stored data           | Monitor for growth trends            |
| Database Query Latency    | Time to execute database queries    | <50ms for simple queries             |
| Resource Streaming Rate   | Rate of streaming resource requests | Monitor for capacity planning        |
| Active Streams            | Number of active SSE streams        | Should align with client connections |

#### Cognition Service Metrics

| Metric                     | Description                          | Target                              |
| -------------------------- | ------------------------------------ | ----------------------------------- |
| Context Generation Latency | Time to generate context             | <200ms for responsive UX            |
| Context Size               | Size of generated context data       | Monitor for unexpected growth       |
| Memory Service Call Rate   | Rate of calls to Memory Service      | Should align with incoming requests |
| Memory Service Latency     | Time for Memory Service to respond   | <100ms                              |
| Processing Queue Depth     | Items waiting for context generation | Should remain low (<10)             |

### Cross-Service Metrics

| Metric                       | Description                                   | Target                            |
| ---------------------------- | --------------------------------------------- | --------------------------------- |
| End-to-End Latency           | Time from request to response across services | <500ms for interactive experience |
| Service Communication Errors | Rate of inter-service communication failures  | <0.1%                             |
| Circuit Breaker Status       | State of circuit breakers for each service    | Mostly closed                     |
| Retry Rate                   | Rate of retried requests between services     | <1%                               |

## Instrumentation

### Instrumentation Principles

1. **Minimize Overhead**: Instrumentation should add minimal performance impact
2. **Focus on Hotspots**: Prioritize instrumenting critical paths and potential bottlenecks
3. **Explicit Timing**: Use explicit timing for key operations rather than sampling
4. **Standardize Naming**: Use consistent metric naming across services
5. **Context Preservation**: Maintain context across service boundaries for tracing

### Built-in Instrumentation

FastAPI provides built-in instrumentation through middleware:

```python
from fastapi import FastAPI, Request
from time import time
import logging

app = FastAPI()

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time()
    response = await call_next(request)
    process_time = time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
```

### Prometheus Instrumentation

For more comprehensive metrics, implement Prometheus instrumentation:

#### 1. Core Service Instrumentation

```python
from prometheus_client import Counter, Histogram, Gauge
from prometheus_client.openmetrics.exposition import generate_latest
from fastapi import FastAPI, Request, Response
from time import time

app = FastAPI()

# Define metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP Request Count',
    ['method', 'endpoint', 'status']
)
REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP Request Latency',
    ['method', 'endpoint']
)
ACTIVE_REQUESTS = Gauge(
    'http_active_requests',
    'Active HTTP Requests',
    ['method', 'endpoint']
)

# Add middleware to track metrics
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    method = request.method
    endpoint = request.url.path

    ACTIVE_REQUESTS.labels(method=method, endpoint=endpoint).inc()

    start_time = time()
    try:
        response = await call_next(request)

        status = response.status_code
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
        REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(time() - start_time)

        return response
    except Exception as e:
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=500).inc()
        raise e
    finally:
        ACTIVE_REQUESTS.labels(method=method, endpoint=endpoint).dec()

# Add metrics endpoint
@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type="text/plain")
```

#### 2. MCP Client Instrumentation

```python
from prometheus_client import Counter, Histogram, Gauge, Summary

# Define MCP client metrics
MCP_REQUEST_COUNT = Counter(
    'mcp_requests_total',
    'Total MCP Request Count',
    ['service', 'tool']
)
MCP_REQUEST_LATENCY = Histogram(
    'mcp_request_duration_seconds',
    'MCP Request Latency',
    ['service', 'tool']
)
MCP_ACTIVE_REQUESTS = Gauge(
    'mcp_active_requests',
    'Active MCP Requests',
    ['service', 'tool']
)
MCP_REQUEST_SIZE = Summary(
    'mcp_request_size_bytes',
    'MCP Request Size',
    ['service', 'tool']
)
MCP_RESPONSE_SIZE = Summary(
    'mcp_response_size_bytes',
    'MCP Response Size',
    ['service', 'tool']
)
MCP_ERROR_COUNT = Counter(
    'mcp_errors_total',
    'MCP Error Count',
    ['service', 'tool', 'error_type']
)
MCP_RETRY_COUNT = Counter(
    'mcp_retries_total',
    'MCP Retry Count',
    ['service', 'tool']
)
MCP_CIRCUIT_STATE = Gauge(
    'mcp_circuit_state',
    'MCP Circuit Breaker State (0=open, 1=half-open, 2=closed)',
    ['service']
)

# Example instrumentation of MCP client call
async def instrumented_call_tool(service, tool, arguments):
    # Record active request
    MCP_ACTIVE_REQUESTS.labels(service=service, tool=tool).inc()

    # Record request size
    request_size = len(json.dumps(arguments))
    MCP_REQUEST_SIZE.labels(service=service, tool=tool).observe(request_size)

    start_time = time()
    try:
        # Make the actual call
        result = await mcp_client.call_tool(service, tool, arguments)

        # Record success and latency
        MCP_REQUEST_COUNT.labels(service=service, tool=tool).inc()
        MCP_REQUEST_LATENCY.labels(service=service, tool=tool).observe(time() - start_time)

        # Record response size
        response_size = len(json.dumps(result))
        MCP_RESPONSE_SIZE.labels(service=service, tool=tool).observe(response_size)

        return result
    except CircuitOpenError as e:
        # Record circuit open error
        MCP_ERROR_COUNT.labels(service=service, tool=tool, error_type="circuit_open").inc()
        raise
    except RetryExhaustedError as e:
        # Record retry exhausted error
        MCP_ERROR_COUNT.labels(service=service, tool=tool, error_type="retry_exhausted").inc()
        raise
    except Exception as e:
        # Record general error
        MCP_ERROR_COUNT.labels(service=service, tool=tool, error_type="other").inc()
        raise
    finally:
        # Always decrement active requests
        MCP_ACTIVE_REQUESTS.labels(service=service, tool=tool).dec()
```

#### 3. Event Bus Instrumentation

```python
from prometheus_client import Counter, Gauge, Histogram

# Define event bus metrics
EVENT_PUBLISH_COUNT = Counter(
    'event_publish_total',
    'Total Event Publish Count',
    ['event_type']
)
EVENT_DELIVERY_COUNT = Counter(
    'event_delivery_total',
    'Total Event Delivery Count',
    ['event_type']
)
EVENT_DELIVERY_ERRORS = Counter(
    'event_delivery_errors_total',
    'Total Event Delivery Errors',
    ['event_type']
)
EVENT_DELIVERY_LATENCY = Histogram(
    'event_delivery_seconds',
    'Event Delivery Latency',
    ['event_type']
)
EVENT_SUBSCRIBERS = Gauge(
    'event_subscribers',
    'Number of Event Subscribers',
    []
)
EVENT_QUEUE_SIZE = Gauge(
    'event_queue_size',
    'Event Queue Size',
    ['subscriber_id']
)

# Instrument event bus publish method
async def publish(self, event):
    event_type = event.get('type', 'unknown')
    EVENT_PUBLISH_COUNT.labels(event_type=event_type).inc()

    # Record current subscriber count
    EVENT_SUBSCRIBERS.set(len(self.subscribers))

    delivery_start = time()
    delivery_count = 0
    error_count = 0

    # Publish to all subscribers
    for subscriber_id, queue in self.subscribers.items():
        try:
            EVENT_QUEUE_SIZE.labels(subscriber_id=subscriber_id).set(queue.qsize())
            await queue.put(event)
            delivery_count += 1
        except Exception as e:
            error_count += 1
            EVENT_DELIVERY_ERRORS.labels(event_type=event_type).inc()

    # Record metrics
    EVENT_DELIVERY_COUNT.labels(event_type=event_type).inc(delivery_count)
    EVENT_DELIVERY_LATENCY.labels(event_type=event_type).observe(time() - delivery_start)
```

### Service-specific Instrumentation

#### Memory Service Instrumentation

```python
from prometheus_client import Counter, Histogram, Gauge

# Define memory service metrics
DB_OPERATION_COUNT = Counter(
    'db_operations_total',
    'Database Operation Count',
    ['operation', 'table']
)
DB_OPERATION_LATENCY = Histogram(
    'db_operation_duration_seconds',
    'Database Operation Latency',
    ['operation', 'table']
)
DB_SIZE = Gauge(
    'db_size_bytes',
    'Database Size in Bytes',
    []
)
DB_CONNECTION_COUNT = Gauge(
    'db_connections',
    'Database Connection Count',
    []
)
DB_CONNECTION_WAIT_TIME = Histogram(
    'db_connection_wait_seconds',
    'Database Connection Wait Time',
    []
)

# Example instrumentation for database operations
async def execute_db_operation(operation, table, query, *args, **kwargs):
    DB_OPERATION_COUNT.labels(operation=operation, table=table).inc()

    start_time = time()
    try:
        # Get connection from pool
        connection_start = time()
        async with database.pool.acquire() as connection:
            DB_CONNECTION_WAIT_TIME.observe(time() - connection_start)

            # Execute query
            result = await connection.execute(query, *args, **kwargs)

            # Record latency
            DB_OPERATION_LATENCY.labels(operation=operation, table=table).observe(time() - start_time)

            return result
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise
    finally:
        # Update connection count and db size periodically
        if random.random() < 0.01:  # 1% chance to avoid excessive overhead
            DB_CONNECTION_COUNT.set(database.pool.size)
            # Update db size (simplified example)
            db_size = await get_db_size()
            DB_SIZE.set(db_size)
```

#### Cognition Service Instrumentation

```python
from prometheus_client import Counter, Histogram, Gauge

# Define cognition service metrics
CONTEXT_GENERATION_COUNT = Counter(
    'context_generation_total',
    'Context Generation Count',
    ['result_type']
)
CONTEXT_GENERATION_LATENCY = Histogram(
    'context_generation_duration_seconds',
    'Context Generation Latency',
    ['result_type']
)
CONTEXT_SIZE = Histogram(
    'context_size_bytes',
    'Context Size in Bytes',
    ['result_type']
)
MEMORY_SERVICE_CALL_COUNT = Counter(
    'memory_service_calls_total',
    'Memory Service Call Count',
    ['operation']
)
MEMORY_SERVICE_LATENCY = Histogram(
    'memory_service_duration_seconds',
    'Memory Service Call Latency',
    ['operation']
)

# Example instrumentation for context generation
async def generate_context(user_id, query=None, limit=10):
    start_time = time()
    result_type = "full"

    try:
        # Call memory service
        memory_call_start = time()
        try:
            history = await memory_client.get_history(user_id, limit=limit)
            MEMORY_SERVICE_CALL_COUNT.labels(operation="get_history").inc()
            MEMORY_SERVICE_LATENCY.labels(operation="get_history").observe(time() - memory_call_start)
        except Exception as e:
            # Record error and use empty history
            MEMORY_SERVICE_CALL_COUNT.labels(operation="get_history_error").inc()
            MEMORY_SERVICE_LATENCY.labels(operation="get_history_error").observe(time() - memory_call_start)
            history = []
            result_type = "fallback"

        # Generate context (simplified)
        context = process_history(history, query)

        # Record metrics
        CONTEXT_GENERATION_COUNT.labels(result_type=result_type).inc()
        CONTEXT_GENERATION_LATENCY.labels(result_type=result_type).observe(time() - start_time)

        # Record context size
        context_size = len(json.dumps(context))
        CONTEXT_SIZE.labels(result_type=result_type).observe(context_size)

        return context
    except Exception as e:
        # Record error
        CONTEXT_GENERATION_COUNT.labels(result_type="error").inc()
        raise
```

## Monitoring Setup

### Prometheus Configuration

Configure Prometheus to scrape metrics from all services. Create a `prometheus.yml` file:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: "core-api"
    scrape_interval: 5s
    static_configs:
      - targets: ["core-api:8000"]
  - job_name: "memory-service"
    scrape_interval: 5s
    static_configs:
      - targets: ["memory-service:9000"]
  - job_name: "cognition-service"
    scrape_interval: 5s
    static_configs:
      - targets: ["cognition-service:9100"]
```

Run Prometheus with Docker:

```bash
docker run -d -p 9090:9090 \
  -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml \
  --name prometheus \
  --network cortex-network \
  prom/prometheus
```

### Grafana Integration

Configure Grafana to visualize Prometheus metrics:

```bash
docker run -d -p 3000:3000 \
  --name grafana \
  --network cortex-network \
  grafana/grafana
```

#### Essential Dashboards

Create the following dashboards in Grafana:

1. **System Overview Dashboard**

   - Service status and health
   - Request rates and error rates
   - End-to-end latency
   - Resource utilization overview

2. **Core API Dashboard**

   - Request volume by endpoint
   - Latency percentiles
   - Active connections
   - Event bus queue sizes
   - MCP client request rates

3. **Memory Service Dashboard**

   - Storage operations
   - Database performance
   - Resource streaming metrics
   - Database size and growth

4. **Cognition Service Dashboard**

   - Context generation latency
   - Memory service call performance
   - Processing queue depth
   - Generated context size

5. **Network Dashboard**
   - Inter-service communication
   - Circuit breaker status
   - Retry rates
   - Network errors

### Alerting

Configure Prometheus alerting rules in `alert.rules.yml`:

```yaml
groups:
  - name: cortex-alerts
    rules:
      # Service health alerts
      - alert: ServiceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service {{ $labels.job }} is down"
          description: "Service {{ $labels.job }} has been down for more than 1 minute."

      # High error rate alerts
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: 'High error rate on {{ $labels.job }} ({{ $value | printf "%.2f" }})'
          description: "Service {{ $labels.job }} has error rate above 5% for more than 2 minutes."

      # Latency alerts
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: 'High latency on {{ $labels.job }} ({{ $value | printf "%.2f" }}s)'
          description: "Service {{ $labels.job }} has 95th percentile latency above 500ms for more than 5 minutes."

      # Resource alerts
      - alert: HighCpuUsage
        expr: process_cpu_seconds_total{job="memory-service"} > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: 'High CPU usage on {{ $labels.job }} ({{ $value | printf "%.2f" }})'
          description: "Service {{ $labels.job }} is using more than 80% CPU for more than 5 minutes."

      # Memory Service specific alerts
      - alert: HighDatabaseLatency
        expr: histogram_quantile(0.95, rate(db_operation_duration_seconds_bucket[5m])) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: 'High database latency on {{ $labels.job }} ({{ $value | printf "%.2f" }}s)'
          description: "Memory Service database operations taking more than 100ms (95th percentile) for over 5 minutes."

      # Circuit breaker alerts
      - alert: CircuitBreakerOpen
        expr: mcp_circuit_state{} == 0
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Circuit breaker open for {{ $labels.service }}"
          description: "The circuit breaker for {{ $labels.service }} has been open for more than 1 minute."
```

### Log Monitoring

Configure log aggregation with Elasticsearch, Fluentd, and Kibana (EFK stack):

#### Fluentd Configuration

Create a `fluentd.conf` file:

```
<source>
  @type forward
  port 24224
  bind 0.0.0.0
</source>

<match *.**>
  @type copy
  <store>
    @type elasticsearch
    host elasticsearch
    port 9200
    logstash_format true
    logstash_prefix fluentd
    logstash_dateformat %Y%m%d
    include_tag_key true
    type_name access_log
    tag_key @log_name
    flush_interval 1s
  </store>
  <store>
    @type stdout
  </store>
</match>
```

Configure services to send logs to Fluentd:

```yaml
# In docker-compose.yml
services:
  core-api:
    # ...
    logging:
      driver: "fluentd"
      options:
        fluentd-address: localhost:24224
        tag: core-api
```

## Performance Baselines

Establish baseline performance for key metrics to identify deviations:

### 1. Request Latency Baselines

| Service           | Endpoint          | P50    | P95    | P99    |
| ----------------- | ----------------- | ------ | ------ | ------ |
| Core API          | /input            | <50ms  | <100ms | <200ms |
| Core API          | /auth/verify      | <10ms  | <30ms  | <50ms  |
| Memory Service    | /tool/store_input | <50ms  | <100ms | <200ms |
| Memory Service    | /resource/history | <30ms  | <80ms  | <150ms |
| Cognition Service | /tool/get_context | <100ms | <200ms | <400ms |

### 2. Throughput Baselines

| Service           | Endpoint          | Baseline RPS  | Max Tested RPS |
| ----------------- | ----------------- | ------------- | -------------- |
| Core API          | /input            | 100           | 500            |
| Core API          | /output/stream    | 50 concurrent | 200 concurrent |
| Memory Service    | /tool/store_input | 150           | 600            |
| Memory Service    | /resource/history | 200           | 800            |
| Cognition Service | /tool/get_context | 100           | 400            |

### 3. Resource Utilization Baselines

| Service           | CPU (idle) | CPU (load) | Memory (idle) | Memory (load) |
| ----------------- | ---------- | ---------- | ------------- | ------------- |
| Core API          | <5%        | <60%       | ~100MB        | ~500MB        |
| Memory Service    | <5%        | <70%       | ~100MB        | ~600MB        |
| Cognition Service | <5%        | <80%       | ~100MB        | ~800MB        |

## Performance Testing

### Load Testing Tools

1. **Locust**: Python-based load testing tool with web UI
2. **wrk**: Command-line HTTP benchmarking tool
3. **hey**: Simple load testing tool

### Load Testing Script Examples

#### Locust Test Script

Create a `locustfile.py`:

```python
import json
import time
from locust import HttpUser, task, between

class CoreApiUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        # Get JWT token
        response = self.client.post("/auth/login", {
            "username": "user@example.com",
            "password": "password123"
        })
        result = response.json()
        self.token = result["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @task(10)
    def submit_input(self):
        self.client.post(
            "/input",
            json={
                "content": f"Test input {time.time()}",
                "metadata": {"test": True}
            },
            headers=self.headers
        )

    @task(1)
    def verify_token(self):
        self.client.get("/auth/verify", headers=self.headers)
```

Run Locust:

```bash
locust -f locustfile.py --host=http://localhost:8000
```

#### wrk Benchmark Script

Create a `post.lua` script:

```lua
wrk.method = "POST"
wrk.body = '{"content": "Test input", "metadata": {"test": true}}'
wrk.headers["Content-Type"] = "application/json"
wrk.headers["Authorization"] = "Bearer YOUR_JWT_TOKEN"
```

Run wrk:

```bash
wrk -t8 -c100 -d30s -s post.lua http://localhost:8000/input
```

### Performance Test Scenarios

1. **Steady Load Test**: Constant request rate for extended period

   ```bash
   hey -n 10000 -c 50 -m POST -H "Authorization: Bearer TOKEN" -H "Content-Type: application/json" -d '{"content":"test"}' http://localhost:8000/input
   ```

2. **Spike Test**: Sudden increase in traffic

   ```bash
   # Run baseline load
   hey -n 5000 -c 20 -m POST -H "Authorization: Bearer TOKEN" -H "Content-Type: application/json" -d '{"content":"test"}' http://localhost:8000/input &

   # After 30 seconds, add spike
   sleep 30 && hey -n 10000 -c 100 -m POST -H "Authorization: Bearer TOKEN" -H "Content-Type: application/json" -d '{"content":"test"}' http://localhost:8000/input
   ```

3. **Endurance Test**: Moderate load for extended period
   ```bash
   hey -n 100000 -c 30 -m POST -H "Authorization: Bearer TOKEN" -H "Content-Type: application/json" -d '{"content":"test"}' http://localhost:8000/input
   ```

## Resource Utilization

### CPU Optimization

1. **Worker Configuration**:

   - Core API: `uvicorn --workers=2*CPU_CORES app.main:app`
   - Memory Service: `uvicorn --workers=CPU_CORES app.main:app`
   - Cognition Service: `uvicorn --workers=2*CPU_CORES app.main:app`

2. **Profiling CPU Usage**:

   ```python
   import cProfile
   import pstats
   import io

   def profile(func):
       def wrapper(*args, **kwargs):
           pr = cProfile.Profile()
           pr.enable()
           result = func(*args, **kwargs)
           pr.disable()
           s = io.StringIO()
           ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
           ps.print_stats(20)
           print(s.getvalue())
           return result
       return wrapper

   @profile
   def cpu_intensive_function():
       # Function code here
       pass
   ```

3. **CPU Bottleneck Identification**:
   - Use `py-spy` for real-time profiling
   - Monitor CPU usage patterns in Prometheus
   - Look for functions with high cumulative time in profiles

### Memory Optimization

1. **Memory Profiling**:

   ```python
   from pympler import tracker
   import gc

   def profile_memory():
       # Get objects before
       tr = tracker.SummaryTracker()

       # Run code to profile
       result = memory_intensive_function()

       # Force garbage collection
       gc.collect()

       # Print memory differences
       tr.print_diff()

       return result
   ```

2. **Common Memory Issues**:

   - Connection pools not being closed
   - SSE connections not cleaned up
   - Large objects stored in request context
   - Excessive caching

3. **Monitoring Memory Leaks**:
   - Track service memory over time
   - Look for steadily increasing memory usage
   - Periodic restarts as a temporary mitigation

### Connection Pooling

1. **Database Connection Pooling**:

   ```python
   from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
   from sqlalchemy.orm import sessionmaker
   from sqlalchemy.pool import QueuePool

   # Create engine with connection pool
   engine = create_async_engine(
       DATABASE_URL,
       poolclass=QueuePool,
       pool_size=10,  # Base pool size
       max_overflow=20,  # Allow additional connections under load
       pool_timeout=30,  # Wait time for connection
       pool_recycle=1800,  # Recycle connections after 30 min
       pool_pre_ping=True  # Verify connections before use
   )

   # Create session factory
   async_session = sessionmaker(
       engine, class_=AsyncSession, expire_on_commit=False
   )
   ```

2. **HTTP Client Connection Pooling**:

   ```python
   import httpx

   # Create client with limits
   client = httpx.AsyncClient(
       limits=httpx.Limits(
           max_keepalive_connections=20,
           max_connections=100,
           keepalive_expiry=30.0
       ),
       timeout=httpx.Timeout(
           connect=5.0,
           read=30.0,
           write=10.0,
           pool=10.0
       )
   )
   ```

3. **MCP Client Connection Pooling**:

   ```python
   class ManagedMcpClient:
       def __init__(self, service_url, pool_size=10):
           self.service_url = service_url
           self.pool_size = pool_size
           self.pool = [None] * pool_size
           self.pool_locks = [asyncio.Lock() for _ in range(pool_size)]

       async def get_client(self):
           # Select client with strategy
           for i in range(self.pool_size):
               if not self.pool_locks[i].locked():
                   async with self.pool_locks[i]:
                       if self.pool[i] is None:
                           # Create new client
                           self.pool[i] = await self._create_client()
                       return i, self.pool[i]

           # All busy, wait for first available
           for i in range(self.pool_size):
               async with self.pool_locks[i]:
                   if self.pool[i] is None:
                       self.pool[i] = await self._create_client()
                   return i, self.pool[i]

       async def _create_client(self):
           # Create and initialize client
           client = McpClient(self.service_url)
           await client.initialize()
           return client

       async def call_tool(self, tool_name, arguments):
           # Get client from pool
           index, client = await self.get_client()
           try:
               # Make call
               return await client.call_tool(tool_name, arguments)
           finally:
               # Release client by releasing lock
               self.pool_locks[index].release()
   ```

## Performance Bottleneck Identification

### Common Bottlenecks

1. **Database Queries**

   - Long-running queries
   - Missing indexes
   - Connection pool exhaustion
   - Query plan issues

2. **Network Communication**

   - Inter-service latency
   - Network saturation
   - Connection establishment overhead
   - SSL/TLS overhead

3. **Resource Exhaustion**

   - CPU saturation
   - Memory exhaustion
   - File descriptor limits
   - Thread pool exhaustion

4. **Serialization/Deserialization**
   - Large object serialization
   - Inefficient serialization formats
   - Unnecessary data transfer

### Bottleneck Identification Strategies

1. **Use the USE Method**: For each resource, check:

   - **Utilization**: Percentage of time resource is busy
   - **Saturation**: Degree to which resource has extra work queued
   - **Errors**: Count of error events

2. **Identify Hot Paths**:

   - Review latency heat maps
   - Find endpoints with highest request rates
   - Examine critical user flows

3. **Database Query Analysis**:

   ```python
   # Add query logging and timing
   async def execute_query(query, *args):
       start_time = time.time()
       try:
           result = await database.execute(query, *args)
           duration = time.time() - start_time

           # Log slow queries (>100ms)
           if duration > 0.1:
               logger.warning(f"Slow query ({duration:.3f}s): {query}")
               SLOW_QUERY_COUNT.inc()

           return result
       except Exception as e:
           logger.error(f"Query error ({time.time() - start_time:.3f}s): {query}, {str(e)}")
           raise
   ```

4. **Flame Graphs**:

   - Use py-spy to generate flame graphs
   - Identify functions consuming most CPU time
   - Look for deep call stacks and recursive patterns

   ```bash
   py-spy record -o profile.svg --pid $PID
   ```

## Performance Optimization Techniques

### 1. Caching Strategies

```python
import functools
import time
import asyncio

# Simple time-based cache decorator
def timed_cache(ttl_seconds=60):
    def decorator(func):
        cache = {}

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key from args and kwargs
            key = str(args) + str(sorted(kwargs.items()))

            # Check if result in cache and fresh
            if key in cache:
                result, timestamp = cache[key]
                if time.time() - timestamp < ttl_seconds:
                    return result

            # Not in cache or expired, call function
            result = await func(*args, **kwargs)

            # Store in cache
            cache[key] = (result, time.time())

            # Schedule cleanup if cache grows too large (simple approach)
            if len(cache) > 1000:
                asyncio.create_task(clean_cache())

            return result

        async def clean_cache():
            """Remove expired items from cache"""
            now = time.time()
            expired_keys = [
                k for k, (_, ts) in cache.items()
                if now - ts > ttl_seconds
            ]
            for k in expired_keys:
                del cache[k]

        # Add helper methods to the wrapper
        wrapper.invalidate = lambda: cache.clear()
        wrapper.cache_info = lambda: {
            "hits": sum(1 for _, ts in cache.values() if time.time() - ts < ttl_seconds),
            "currsize": len(cache)
        }

        return wrapper
    return decorator

# Usage example
@timed_cache(ttl_seconds=300)  # 5 minute cache
async def get_user_context(user_id):
    # Expensive operation to get user context
    context = await cognition_service.get_context(user_id)
    return context
```

### 2. Batch Processing

```python
class BatchProcessor:
    def __init__(self, process_func, max_batch_size=100, max_wait_time=0.1):
        self.process_func = process_func
        self.max_batch_size = max_batch_size
        self.max_wait_time = max_wait_time
        self.queue = asyncio.Queue()
        self.processing_task = None
        self.shutdown_event = asyncio.Event()

    async def start(self):
        """Start the batch processor"""
        self.processing_task = asyncio.create_task(self._processing_loop())

    async def stop(self):
        """Stop the batch processor"""
        self.shutdown_event.set()
        if self.processing_task:
            await self.processing_task

    async def add_item(self, item):
        """Add item to batch with future for result"""
        future = asyncio.Future()
        await self.queue.put((item, future))
        return await future

    async def _processing_loop(self):
        """Main processing loop"""
        while not self.shutdown_event.is_set():
            # Collect batch
            batch = []
            futures = []

            # Get first item (with timeout)
            try:
                item, future = await asyncio.wait_for(
                    self.queue.get(),
                    timeout=self.max_wait_time
                )
                batch.append(item)
                futures.append(future)
                self.queue.task_done()
            except asyncio.TimeoutError:
                # No items, continue loop
                continue

            # Try to collect more items up to max batch size
            batch_size = 1
            while batch_size < self.max_batch_size and not self.queue.empty():
                item, future = await self.queue.get()
                batch.append(item)
                futures.append(future)
                batch_size += 1
                self.queue.task_done()

            # Process batch
            try:
                results = await self.process_func(batch)
                # Set results to futures
                for future, result in zip(futures, results):
                    future.set_result(result)
            except Exception as e:
                # Set exception to all futures
                for future in futures:
                    future.set_exception(e)

# Usage example for database operations
batch_processor = BatchProcessor(bulk_insert_items)
await batch_processor.start()

# Add items
result = await batch_processor.add_item(item)
```

### 3. Asynchronous Processing

```python
class BackgroundTaskManager:
    def __init__(self, max_workers=10):
        self.max_workers = max_workers
        self.running_tasks = set()
        self.semaphore = asyncio.Semaphore(max_workers)

    async def run_task(self, coro):
        """Run a coroutine as a background task with limits"""
        async with self.semaphore:
            task = asyncio.create_task(coro)
            self.running_tasks.add(task)
            try:
                return await task
            finally:
                self.running_tasks.remove(task)

    def schedule_task(self, coro):
        """Schedule a task to run in the background"""
        async def _wrapped():
            async with self.semaphore:
                task = asyncio.create_task(coro)
                self.running_tasks.add(task)
                try:
                    await task
                except Exception as e:
                    logger.error(f"Background task error: {e}")
                finally:
                    self.running_tasks.remove(task)

        asyncio.create_task(_wrapped())

    async def wait_all(self):
        """Wait for all running tasks to complete"""
        if self.running_tasks:
            await asyncio.gather(*self.running_tasks, return_exceptions=True)

# Usage example
task_manager = BackgroundTaskManager(max_workers=5)

# Run important task and wait for result
result = await task_manager.run_task(important_coro())

# Schedule non-critical task and don't wait
task_manager.schedule_task(non_critical_coro())
```

### 4. Database Optimization

1. **Add proper indexes**:

   ```sql
   -- Add index for queries on user_id
   CREATE INDEX idx_user_history_user_id ON user_history(user_id);

   -- Add index for timestamp-based queries
   CREATE INDEX idx_user_history_timestamp ON user_history(timestamp DESC);

   -- Add composite index for common query pattern
   CREATE INDEX idx_user_history_user_timestamp ON user_history(user_id, timestamp DESC);
   ```

2. **Use efficient queries**:

   ```python
   # Instead of:
   count = await db.execute("SELECT COUNT(*) FROM user_history WHERE user_id = ?", user_id)

   # Use:
   exists = await db.execute("SELECT 1 FROM user_history WHERE user_id = ? LIMIT 1", user_id)
   ```

3. **Denormalize for read-heavy workloads**:
   ```python
   # Store pre-computed data to avoid joins
   user_summary = {
       "user_id": user_id,
       "total_interactions": interaction_count,
       "last_active": last_timestamp,
       "common_topics": common_topics
   }
   await db.execute("INSERT INTO user_summary (user_id, data) VALUES (?, ?)",
                   user_id, json.dumps(user_summary))
   ```

## Advanced Monitoring

### Distributed Tracing

Implement OpenTelemetry tracing:

```python
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Configure tracer
def setup_tracing(app, service_name):
    resource = Resource(attributes={SERVICE_NAME: service_name})

    # Set up trace exporter (Jaeger)
    jaeger_exporter = JaegerExporter(
        agent_host_name="jaeger",
        agent_port=6831,
    )

    # Set up trace provider
    provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(jaeger_exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)

    # Create tracer
    return trace.get_tracer(service_name)

# Example usage
app = FastAPI()
tracer = setup_tracing(app, "core-api")

@app.post("/input")
async def receive_input(request: dict):
    # Create span for this operation
    with tracer.start_as_current_span("process_input") as span:
        # Add attributes to the span
        span.set_attribute("user_id", request.get("user_id"))

        # Process input
        result = await process_input(request)

        # Add result info to span
        span.set_attribute("status", "success")

        return result
```

### Runtime Profiling

Set up continuous profiling with pyroscope:

```python
import pyroscope
import os

# Initialize pyroscope
pyroscope.configure(
    application_name="core-api",
    server_address="http://pyroscope:4040",
    auth_token=os.getenv("PYROSCOPE_TOKEN", ""),
    tags={
        "service": "core-api",
        "environment": os.getenv("ENVIRONMENT", "development")
    }
)

# Start profiling
pyroscope.start()
```

Run pyroscope:

```bash
docker run -d --name pyroscope -p 4040:4040 pyroscope/pyroscope:latest server
```

## Best Practices

### 1. Establish Monitoring Early

Implement basic monitoring from the start:

```python
# Add to service startup
async def startup_event():
    # Set up Prometheus metrics
    setup_prometheus_metrics()

    # Set up health check that includes all dependencies
    @app.get("/health")
    async def health_check():
        # Check database
        db_healthy = await check_database_health()

        # Check dependent services
        memory_healthy = await check_memory_service_health()

        # Overall health
        is_healthy = db_healthy and memory_healthy

        # Return health status
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "checks": {
                "database": "healthy" if db_healthy else "unhealthy",
                "memory_service": "healthy" if memory_healthy else "unhealthy",
            },
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
```

### 2. Only Optimize When Necessary

Focus optimization efforts based on data:

```python
# Simple profiling decorator to identify bottlenecks
def profile_endpoint(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            return await func(*args, **kwargs)
        finally:
            elapsed = time.time() - start_time
            # Only log if slow (>100ms)
            if elapsed > 0.1:
                logger.info(f"Slow endpoint {func.__name__}: {elapsed:.3f}s")
    return wrapper

# Apply to endpoints selectively
@app.post("/input")
@profile_endpoint
async def receive_input(request: dict):
    # Endpoint implementation
    pass
```

### 3. Regular Performance Testing

Integrate performance testing into CI/CD:

```yaml
# Example GitHub Actions workflow
name: Performance Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  performance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Set up services
        run: docker-compose up -d

      - name: Wait for services to stabilize
        run: sleep 10

      - name: Run performance tests
        run: locust -f tests/performance/locustfile.py --headless -u 50 -r 10 -t 1m

      - name: Check results against baselines
        run: python tests/performance/check_results.py
```

### 4. Resource Constraint Testing

Test with limited resources to identify bottlenecks:

```bash
# Run with constrained CPU
docker run --cpus=0.5 -m 256m core-api

# Run load test against constrained service
hey -n 1000 -c 20 http://localhost:8000/health
```

### 5. Graceful Degradation

Implement backup strategies for service failures:

```python
async def get_user_history(user_id):
    try:
        # Try primary method
        return await memory_service.get_history(user_id)
    except CircuitOpenError:
        # Memory service unavailable, use cache
        logger.warning(f"Memory service unavailable, using cache for {user_id}")
        return await get_cached_history(user_id)
    except Exception as e:
        # Unexpected error, fall back to empty history
        logger.error(f"Error getting history: {e}")
        return []
```

## Conclusion

Performance monitoring and optimization in a distributed system require a thoughtful, data-driven approach. By implementing the strategies in this document, you'll be able to establish a solid monitoring foundation, identify bottlenecks proactively, and implement targeted optimizations that improve the overall system performance without unnecessary complexity.

Remember these key principles:

1. **Instrument First**: Add basic metrics and health checks from the beginning
2. **Establish Baselines**: Know what "normal" looks like before optimizing
3. **Measure Before Optimizing**: Use data to guide optimization efforts
4. **Begin Simple**: Start with basic monitoring and enhance as needed
5. **Prioritize User Experience**: Focus on metrics that directly impact users
6. **Automate Testing**: Include performance tests in your CI/CD pipeline
7. **Plan for Failure**: Design for graceful degradation under load
8. **Document Patterns**: Record successful optimization techniques

By following these guidelines, you'll create a robust, high-performing distributed system that can scale to meet your needs while maintaining responsiveness and reliability.
