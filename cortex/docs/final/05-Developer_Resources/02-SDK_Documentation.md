# SDK Documentation

_Version: 1.0_  
_Date: 2025-03-05_

## Overview

This document provides detailed documentation for the official Cortex Platform SDKs. These SDKs enable developers to integrate with the Cortex Platform using their preferred programming language.

## Available SDKs

The Cortex Platform provides official SDKs for the following languages:

| Language              | Package Name              | Latest Version | Min Language Version |
| --------------------- | ------------------------- | -------------- | -------------------- |
| JavaScript/TypeScript | `@cortex-platform/sdk`    | 1.2.0          | ES6, TypeScript 4.5+ |
| Python                | `cortex-platform`         | 1.1.3          | Python 3.8+          |
| Java                  | `com.cortex-platform.sdk` | 1.0.5          | Java 11+             |
| C#                    | `CortexPlatform.SDK`      | 1.0.2          | .NET 6.0+            |

## Installation

### JavaScript/TypeScript

```bash
# Using npm
npm install @cortex-platform/sdk

# Using yarn
yarn add @cortex-platform/sdk

# Using pnpm
pnpm add @cortex-platform/sdk
```

### Python

```bash
# Using pip
pip install cortex-platform

# Using pipenv
pipenv install cortex-platform

# Using poetry
poetry add cortex-platform
```

### Java

**Maven:**

```xml
<dependency>
  <groupId>com.cortex-platform</groupId>
  <artifactId>sdk</artifactId>
  <version>1.0.5</version>
</dependency>
```

**Gradle:**

```groovy
implementation 'com.cortex-platform:sdk:1.0.5'
```

### C#

**NuGet Package Manager:**

```bash
Install-Package CortexPlatform.SDK
```

**.NET CLI:**

```bash
dotnet add package CortexPlatform.SDK
```

## Authentication

All SDKs provide similar authentication patterns using API keys.

### JavaScript/TypeScript

```typescript
import { CortexClient } from "@cortex-platform/sdk";

// Initialize with API key
const cortex = new CortexClient({
  apiKey: "your_api_key",
  environment: "production", // or 'sandbox'
});

// Alternatively, initialize with OAuth
const cortex = new CortexClient({
  clientId: "your_client_id",
  clientSecret: "your_client_secret",
  environment: "production",
});

// The SDK will handle token refreshing automatically
```

### Python

```python
from cortex_platform import CortexClient

# Initialize with API key
cortex = CortexClient(
    api_key='your_api_key',
    environment='production'  # or 'sandbox'
)

# Alternatively, initialize with OAuth
cortex = CortexClient(
    client_id='your_client_id',
    client_secret='your_client_secret',
    environment='production'
)

# The SDK will handle token refreshing automatically
```

### Java

```java
import com.cortexplatform.sdk.CortexClient;
import com.cortexplatform.sdk.auth.ApiKeyAuth;
import com.cortexplatform.sdk.auth.OAuthCredentials;

// Initialize with API key
CortexClient cortex = CortexClient.builder()
    .withApiKey("your_api_key")
    .withEnvironment(Environment.PRODUCTION)
    .build();

// Alternatively, initialize with OAuth
CortexClient cortex = CortexClient.builder()
    .withOAuth(new OAuthCredentials("your_client_id", "your_client_secret"))
    .withEnvironment(Environment.PRODUCTION)
    .build();

// The SDK will handle token refreshing automatically
```

### C#

```csharp
using CortexPlatform.SDK;
using CortexPlatform.SDK.Auth;

// Initialize with API key
var cortex = new CortexClient(
    apiKey: "your_api_key",
    environment: Environment.Production
);

// Alternatively, initialize with OAuth
var cortex = new CortexClient(
    new OAuthCredentials(
        clientId: "your_client_id",
        clientSecret: "your_client_secret"
    ),
    environment: Environment.Production
);

// The SDK will handle token refreshing automatically
```

## Core Features

All SDKs provide a consistent interface to the Cortex Platform core features.

### Conversation Management

#### JavaScript/TypeScript

```typescript
// Create a conversation
const conversation = await cortex.conversations.create({
  title: "Project Discussion",
  metadata: { project: "Cortex Implementation" },
});

console.log(`Created conversation: ${conversation.id}`);

// List conversations
const { conversations, pagination } = await cortex.conversations.list({
  limit: 10,
  offset: 0,
});

// Get conversation details
const conversationDetails = await cortex.conversations.get(conversation.id);
```

#### Python

```python
# Create a conversation
conversation = cortex.conversations.create(
    title="Project Discussion",
    metadata={"project": "Cortex Implementation"}
)

print(f"Created conversation: {conversation.id}")

# List conversations
result = cortex.conversations.list(limit=10, offset=0)
conversations = result.conversations
pagination = result.pagination

# Get conversation details
conversation_details = cortex.conversations.get(conversation.id)
```

#### Java

```java
// Create a conversation
ConversationRequest request = new ConversationRequest.Builder()
    .title("Project Discussion")
    .metadata(Map.of("project", "Cortex Implementation"))
    .build();

Conversation conversation = cortex.conversations().create(request);
System.out.println("Created conversation: " + conversation.getId());

// List conversations
ConversationListResult result = cortex.conversations().list(
    new ListOptions.Builder().limit(10).offset(0).build()
);
List<Conversation> conversations = result.getConversations();
Pagination pagination = result.getPagination();

// Get conversation details
Conversation conversationDetails = cortex.conversations().get(conversation.getId());
```

#### C#

```csharp
// Create a conversation
var conversation = await cortex.Conversations.CreateAsync(new ConversationRequest
{
    Title = "Project Discussion",
    Metadata = new Dictionary<string, string>
    {
        ["project"] = "Cortex Implementation"
    }
});

Console.WriteLine($"Created conversation: {conversation.Id}");

// List conversations
var result = await cortex.Conversations.ListAsync(new ListOptions
{
    Limit = 10,
    Offset = 0
});
var conversations = result.Conversations;
var pagination = result.Pagination;

// Get conversation details
var conversationDetails = await cortex.Conversations.GetAsync(conversation.Id);
```

### Message Management

#### JavaScript/TypeScript

```typescript
// Send a message
const message = await cortex.messages.create(conversationId, {
  content: "What can you tell me about the Cortex Platform?",
  role: "user",
  modality: "text",
});

// List messages in a conversation
const { messages } = await cortex.messages.list(conversationId, {
  limit: 20,
});

// Real-time messaging with streaming
const stream = await cortex.messages.createStreamed(conversationId, {
  content: "Generate a detailed report on AI trends",
  role: "user",
  modality: "text",
});

stream.on("data", (chunk) => {
  console.log(chunk.content);
});

stream.on("error", (err) => {
  console.error("Stream error:", err);
});

stream.on("end", () => {
  console.log("Stream complete");
});
```

#### Python

```python
# Send a message
message = cortex.messages.create(
    conversation_id=conversation_id,
    content="What can you tell me about the Cortex Platform?",
    role="user",
    modality="text"
)

# List messages in a conversation
result = cortex.messages.list(
    conversation_id=conversation_id,
    limit=20
)

# Real-time messaging with streaming
with cortex.messages.create_streamed(
    conversation_id=conversation_id,
    content="Generate a detailed report on AI trends",
    role="user",
    modality="text"
) as stream:
    for chunk in stream:
        print(chunk.content, end="", flush=True)
    print()  # Final newline
```

#### Java

```java
// Send a message
Message message = cortex.messages().create(
    conversationId,
    new MessageRequest.Builder()
        .content("What can you tell me about the Cortex Platform?")
        .role(Role.USER)
        .modality(Modality.TEXT)
        .build()
);

// List messages in a conversation
MessageListResult result = cortex.messages().list(
    conversationId,
    new ListOptions.Builder().limit(20).build()
);

// Real-time messaging with streaming
try (MessageStream stream = cortex.messages().createStreamed(
    conversationId,
    new MessageRequest.Builder()
        .content("Generate a detailed report on AI trends")
        .role(Role.USER)
        .modality(Modality.TEXT)
        .build()
)) {
    stream.onData(chunk -> System.out.print(chunk.getContent()));
    stream.onError(err -> System.err.println("Stream error: " + err.getMessage()));
    stream.onComplete(() -> System.out.println()); // Final newline

    // Wait for stream to complete
    stream.await();
}
```

#### C#

```csharp
// Send a message
var message = await cortex.Messages.CreateAsync(
    conversationId,
    new MessageRequest
    {
        Content = "What can you tell me about the Cortex Platform?",
        Role = Role.User,
        Modality = Modality.Text
    }
);

// List messages in a conversation
var result = await cortex.Messages.ListAsync(
    conversationId,
    new ListOptions { Limit = 20 }
);

// Real-time messaging with streaming
await foreach (var chunk in cortex.Messages.CreateStreamedAsync(
    conversationId,
    new MessageRequest
    {
        Content = "Generate a detailed report on AI trends",
        Role = Role.User,
        Modality = Modality.Text
    }
))
{
    Console.Write(chunk.Content);
}
Console.WriteLine(); // Final newline
```

### Memory Management

#### JavaScript/TypeScript

```typescript
// Store information in memory
const memoryItem = await cortex.memory.store({
  entityType: "document",
  entityId: "doc_abc123",
  content: "This is an important document containing...",
  metadata: {
    title: "Important Document",
    tags: ["research", "ai", "cortex"],
  },
});

// Retrieve information from memory
const results = await cortex.memory.retrieve({
  query: "important ai research",
  entityType: "document",
  limit: 5,
});

// Results are sorted by relevance
for (const item of results) {
  console.log(`${item.metadata.title} (Score: ${item.relevanceScore})`);
}
```

#### Python

```python
# Store information in memory
memory_item = cortex.memory.store(
    entity_type="document",
    entity_id="doc_abc123",
    content="This is an important document containing...",
    metadata={
        "title": "Important Document",
        "tags": ["research", "ai", "cortex"]
    }
)

# Retrieve information from memory
results = cortex.memory.retrieve(
    query="important ai research",
    entity_type="document",
    limit=5
)

# Results are sorted by relevance
for item in results:
    print(f"{item.metadata['title']} (Score: {item.relevance_score})")
```

#### Java

```java
// Store information in memory
MemoryItem memoryItem = cortex.memory().store(
    new MemoryStoreRequest.Builder()
        .entityType("document")
        .entityId("doc_abc123")
        .content("This is an important document containing...")
        .metadata(Map.of(
            "title", "Important Document",
            "tags", List.of("research", "ai", "cortex")
        ))
        .build()
);

// Retrieve information from memory
List<MemoryItem> results = cortex.memory().retrieve(
    new MemoryRetrieveRequest.Builder()
        .query("important ai research")
        .entityType("document")
        .limit(5)
        .build()
);

// Results are sorted by relevance
for (MemoryItem item : results) {
    System.out.printf("%s (Score: %.2f)%n",
        item.getMetadata().get("title"),
        item.getRelevanceScore());
}
```

#### C#

```csharp
// Store information in memory
var memoryItem = await cortex.Memory.StoreAsync(new MemoryStoreRequest
{
    EntityType = "document",
    EntityId = "doc_abc123",
    Content = "This is an important document containing...",
    Metadata = new Dictionary<string, object>
    {
        ["title"] = "Important Document",
        ["tags"] = new[] { "research", "ai", "cortex" }
    }
});

// Retrieve information from memory
var results = await cortex.Memory.RetrieveAsync(new MemoryRetrieveRequest
{
    Query = "important ai research",
    EntityType = "document",
    Limit = 5
});

// Results are sorted by relevance
foreach (var item in results)
{
    Console.WriteLine($"{item.Metadata["title"]} (Score: {item.RelevanceScore})");
}
```

### Domain Expert APIs

#### JavaScript/TypeScript

```typescript
// Code Assistant - Analyze code
const analysis = await cortex.experts.code.analyze({
  code: "function calculateTotal(items) {\n  // Code here...\n}",
  language: "javascript",
  analysisType: ["performance", "security", "style"],
});

// Deep Research - Perform research
const research = await cortex.experts.research.query({
  query: "What are the latest developments in quantum computing?",
  depth: "comprehensive",
  sources: ["academic", "news", "patents"],
});

// Check research status
const researchStatus = await cortex.experts.research.getStatus(research.id);

// Get research results when complete
if (researchStatus.status === "completed") {
  const results = await cortex.experts.research.getResults(research.id);
  console.log(results.summary);
}
```

#### Python

```python
# Code Assistant - Analyze code
analysis = cortex.experts.code.analyze(
    code="function calculateTotal(items) {\n  // Code here...\n}",
    language="javascript",
    analysis_type=["performance", "security", "style"]
)

# Deep Research - Perform research
research = cortex.experts.research.query(
    query="What are the latest developments in quantum computing?",
    depth="comprehensive",
    sources=["academic", "news", "patents"]
)

# Check research status
research_status = cortex.experts.research.get_status(research.id)

# Get research results when complete
if research_status.status == "completed":
    results = cortex.experts.research.get_results(research.id)
    print(results.summary)
```

#### Java

```java
// Code Assistant - Analyze code
CodeAnalysis analysis = cortex.experts().code().analyze(
    new CodeAnalysisRequest.Builder()
        .code("function calculateTotal(items) {\n  // Code here...\n}")
        .language("javascript")
        .analysisType(List.of("performance", "security", "style"))
        .build()
);

// Deep Research - Perform research
Research research = cortex.experts().research().query(
    new ResearchQueryRequest.Builder()
        .query("What are the latest developments in quantum computing?")
        .depth(ResearchDepth.COMPREHENSIVE)
        .sources(List.of("academic", "news", "patents"))
        .build()
);

// Check research status
ResearchStatus researchStatus = cortex.experts().research().getStatus(research.getId());

// Get research results when complete
if (researchStatus.getStatus() == Status.COMPLETED) {
    ResearchResults results = cortex.experts().research().getResults(research.getId());
    System.out.println(results.getSummary());
}
```

#### C#

```csharp
// Code Assistant - Analyze code
var analysis = await cortex.Experts.Code.AnalyzeAsync(new CodeAnalysisRequest
{
    Code = "function calculateTotal(items) {\n  // Code here...\n}",
    Language = "javascript",
    AnalysisType = new[] { "performance", "security", "style" }
});

// Deep Research - Perform research
var research = await cortex.Experts.Research.QueryAsync(new ResearchQueryRequest
{
    Query = "What are the latest developments in quantum computing?",
    Depth = ResearchDepth.Comprehensive,
    Sources = new[] { "academic", "news", "patents" }
});

// Check research status
var researchStatus = await cortex.Experts.Research.GetStatusAsync(research.Id);

// Get research results when complete
if (researchStatus.Status == Status.Completed)
{
    var results = await cortex.Experts.Research.GetResultsAsync(research.Id);
    Console.WriteLine(results.Summary);
}
```

## Error Handling

All SDKs provide standardized error handling mechanisms.

### JavaScript/TypeScript

```typescript
try {
  const conversation = await cortex.conversations.create({
    title: "Project Discussion",
  });
  console.log(`Created conversation: ${conversation.id}`);
} catch (error) {
  if (error instanceof cortex.ApiError) {
    console.error(`API Error (${error.statusCode}): ${error.message}`);
    console.error(`Request ID: ${error.requestId}`);

    if (error.details) {
      for (const detail of error.details) {
        console.error(`- ${detail.field}: ${detail.issue}`);
      }
    }
  } else {
    console.error(`Unexpected error: ${error.message}`);
  }
}
```

### Python

```python
try:
    conversation = cortex.conversations.create(
        title="Project Discussion"
    )
    print(f"Created conversation: {conversation.id}")
except cortex_platform.ApiError as error:
    print(f"API Error ({error.status_code}): {error.message}")
    print(f"Request ID: {error.request_id}")

    if error.details:
        for detail in error.details:
            print(f"- {detail.field}: {detail.issue}")
except Exception as error:
    print(f"Unexpected error: {str(error)}")
```

### Java

```java
try {
    ConversationRequest request = new ConversationRequest.Builder()
        .title("Project Discussion")
        .build();

    Conversation conversation = cortex.conversations().create(request);
    System.out.println("Created conversation: " + conversation.getId());
} catch (ApiException error) {
    System.err.printf("API Error (%d): %s%n", error.getStatusCode(), error.getMessage());
    System.err.println("Request ID: " + error.getRequestId());

    if (error.getDetails() != null) {
        for (ErrorDetail detail : error.getDetails()) {
            System.err.printf("- %s: %s%n", detail.getField(), detail.getIssue());
        }
    }
} catch (Exception error) {
    System.err.println("Unexpected error: " + error.getMessage());
}
```

### C#

```csharp
try
{
    var conversation = await cortex.Conversations.CreateAsync(new ConversationRequest
    {
        Title = "Project Discussion"
    });
    Console.WriteLine($"Created conversation: {conversation.Id}");
}
catch (ApiException error)
{
    Console.Error.WriteLine($"API Error ({error.StatusCode}): {error.Message}");
    Console.Error.WriteLine($"Request ID: {error.RequestId}");

    if (error.Details != null)
    {
        foreach (var detail in error.Details)
        {
            Console.Error.WriteLine($"- {detail.Field}: {detail.Issue}");
        }
    }
}
catch (Exception error)
{
    Console.Error.WriteLine($"Unexpected error: {error.Message}");
}
```

## Advanced Features

### Retry and Circuit Breaker Policies

All SDKs provide configurable retry and circuit breaker policies.

#### JavaScript/TypeScript

```typescript
import { CortexClient, RetryPolicy } from "@cortex-platform/sdk";

const cortex = new CortexClient({
  apiKey: "your_api_key",
  retryPolicy: new RetryPolicy({
    maxRetries: 3,
    initialDelay: 1000,
    maxDelay: 10000,
    backoffFactor: 2,
    retryableStatusCodes: [429, 503],
  }),
  circuitBreaker: {
    failureThreshold: 5,
    resetTimeout: 30000,
  },
});
```

#### Python

```python
from cortex_platform import CortexClient, RetryPolicy, CircuitBreakerPolicy

cortex = CortexClient(
    api_key='your_api_key',
    retry_policy=RetryPolicy(
        max_retries=3,
        initial_delay=1000,
        max_delay=10000,
        backoff_factor=2,
        retryable_status_codes=[429, 503]
    ),
    circuit_breaker=CircuitBreakerPolicy(
        failure_threshold=5,
        reset_timeout=30000
    )
)
```

#### Java

```java
import com.cortexplatform.sdk.CortexClient;
import com.cortexplatform.sdk.policies.RetryPolicy;
import com.cortexplatform.sdk.policies.CircuitBreakerPolicy;

CortexClient cortex = CortexClient.builder()
    .withApiKey("your_api_key")
    .withRetryPolicy(new RetryPolicy.Builder()
        .maxRetries(3)
        .initialDelay(1000)
        .maxDelay(10000)
        .backoffFactor(2)
        .retryableStatusCodes(List.of(429, 503))
        .build())
    .withCircuitBreaker(new CircuitBreakerPolicy.Builder()
        .failureThreshold(5)
        .resetTimeout(30000)
        .build())
    .build();
```

#### C#

```csharp
using CortexPlatform.SDK;
using CortexPlatform.SDK.Policies;

var cortex = new CortexClient(
    apiKey: "your_api_key",
    retryPolicy: new RetryPolicy
    {
        MaxRetries = 3,
        InitialDelay = TimeSpan.FromSeconds(1),
        MaxDelay = TimeSpan.FromSeconds(10),
        BackoffFactor = 2,
        RetryableStatusCodes = new[] { 429, 503 }
    },
    circuitBreaker: new CircuitBreakerPolicy
    {
        FailureThreshold = 5,
        ResetTimeout = TimeSpan.FromSeconds(30)
    }
);
```

### Caching

All SDKs provide configurable caching to improve performance.

#### JavaScript/TypeScript

```typescript
import { CortexClient, MemoryCache } from "@cortex-platform/sdk";

const cortex = new CortexClient({
  apiKey: "your_api_key",
  cache: new MemoryCache({
    maxSize: 100,
    ttl: 300000, // 5 minutes
  }),
});

// Or use Redis cache
import { RedisCache } from "@cortex-platform/sdk-redis";

const cortex = new CortexClient({
  apiKey: "your_api_key",
  cache: new RedisCache({
    host: "localhost",
    port: 6379,
    ttl: 300000, // 5 minutes
  }),
});
```

#### Python

```python
from cortex_platform import CortexClient, MemoryCache
from cortex_platform.redis import RedisCache

# Memory cache
cortex = CortexClient(
    api_key='your_api_key',
    cache=MemoryCache(
        max_size=100,
        ttl=300  # 5 minutes
    )
)

# Or use Redis cache
cortex = CortexClient(
    api_key='your_api_key',
    cache=RedisCache(
        host='localhost',
        port=6379,
        ttl=300  # 5 minutes
    )
)
```

#### Java

```java
import com.cortexplatform.sdk.CortexClient;
import com.cortexplatform.sdk.cache.MemoryCache;
import com.cortexplatform.sdk.cache.redis.RedisCache;

// Memory cache
CortexClient cortex = CortexClient.builder()
    .withApiKey("your_api_key")
    .withCache(new MemoryCache.Builder()
        .maxSize(100)
        .ttl(Duration.ofMinutes(5))
        .build())
    .build();

// Or use Redis cache
CortexClient cortex = CortexClient.builder()
    .withApiKey("your_api_key")
    .withCache(new RedisCache.Builder()
        .host("localhost")
        .port(6379)
        .ttl(Duration.ofMinutes(5))
        .build())
    .build();
```

#### C#

```csharp
using CortexPlatform.SDK;
using CortexPlatform.SDK.Cache;
using CortexPlatform.SDK.Cache.Redis;

// Memory cache
var cortex = new CortexClient(
    apiKey: "your_api_key",
    cache: new MemoryCache
    {
        MaxSize = 100,
        Ttl = TimeSpan.FromMinutes(5)
    }
);

// Or use Redis cache
var cortex = new CortexClient(
    apiKey: "your_api_key",
    cache: new RedisCache
    {
        Host = "localhost",
        Port = 6379,
        Ttl = TimeSpan.FromMinutes(5)
    }
);
```

### Logging

All SDKs provide configurable logging.

#### JavaScript/TypeScript

```typescript
import { CortexClient, LogLevel } from "@cortex-platform/sdk";

const cortex = new CortexClient({
  apiKey: "your_api_key",
  logLevel: LogLevel.DEBUG,
  logger: (level, message, metadata) => {
    console.log(`[${level}] ${message}`, metadata);
  },
});
```

#### Python

```python
import logging
from cortex_platform import CortexClient, LogLevel

# Configure Python logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('cortex_platform')

# Use with SDK
cortex = CortexClient(
    api_key='your_api_key',
    log_level=LogLevel.DEBUG,
    logger=logger
)
```

#### Java

```java
import com.cortexplatform.sdk.CortexClient;
import com.cortexplatform.sdk.logging.LogLevel;
import org.slf4j.LoggerFactory;

// Using SLF4J
CortexClient cortex = CortexClient.builder()
    .withApiKey("your_api_key")
    .withLogLevel(LogLevel.DEBUG)
    .withLogger(LoggerFactory.getLogger("cortex-platform"))
    .build();
```

#### C#

```csharp
using CortexPlatform.SDK;
using CortexPlatform.SDK.Logging;
using Microsoft.Extensions.Logging;

// Using ILogger
var loggerFactory = LoggerFactory.Create(builder => {
    builder.AddConsole();
    builder.SetMinimumLevel(Microsoft.Extensions.Logging.LogLevel.Debug);
});

var cortex = new CortexClient(
    apiKey: "your_api_key",
    logLevel: LogLevel.Debug,
    logger: loggerFactory.CreateLogger<CortexClient>()
);
```

## Framework Integrations

### React Integration

```typescript
import { useCortex } from "@cortex-platform/react";

function ChatComponent() {
  const { cortex, isAuthenticated, isLoading, error } = useCortex();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");

  useEffect(() => {
    if (isAuthenticated) {
      loadMessages();
    }
  }, [isAuthenticated]);

  async function loadMessages() {
    const conversation = await cortex.conversations.create();
    const { messages } = await cortex.messages.list(conversation.id);
    setMessages(messages);
  }

  async function sendMessage() {
    if (!input.trim()) return;

    const message = await cortex.messages.create(conversation.id, {
      content: input,
      role: "user",
      modality: "text",
    });

    setMessages([...messages, message]);
    setInput("");
  }

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;
  if (!isAuthenticated) return <div>Not authenticated</div>;

  return (
    <div>
      <div className="messages">
        {messages.map((msg) => (
          <div key={msg.id} className={`message ${msg.role}`}>
            {msg.content}
          </div>
        ))}
      </div>
      <div className="input">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message..."
        />
        <button onClick={sendMessage}>Send</button>
      </div>
    </div>
  );
}
```

### Django Integration

```python
# settings.py
INSTALLED_APPS = [
    # ...
    'cortex_platform.django',
]

CORTEX_PLATFORM = {
    'API_KEY': 'your_api_key',
    'ENVIRONMENT': 'production',
    'CACHE': {
        'BACKEND': 'cortex_platform.django.cache.DjangoCache',
        'OPTIONS': {
            'TIMEOUT': 300  # 5 minutes
        }
    }
}

# views.py
from django.shortcuts import render
from cortex_platform.django.decorators import cortex_enabled

@cortex_enabled
def chat_view(request, cortex):
    if request.method == 'POST':
        message_content = request.POST.get('message')
        conversation_id = request.session.get('conversation_id')

        if not conversation_id:
            conversation = cortex.conversations.create()
            conversation_id = conversation.id
            request.session['conversation_id'] = conversation_id

        message = cortex.messages.create(
            conversation_id=conversation_id,
            content=message_content,
            role='user',
            modality='text'
        )

    conversation_id = request.session.get('conversation_id')
    messages = []

    if conversation_id:
        result = cortex.messages.list(conversation_id)
        messages = result.messages

    return render(request, 'chat.html', {
        'messages': messages
    })
```

### Spring Boot Integration

```java
// Configuration
import com.cortexplatform.sdk.CortexClient;
import com.cortexplatform.sdk.spring.EnableCortexPlatform;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
@EnableCortexPlatform
public class CortexConfig {
    @Bean
    public CortexClient cortexClient() {
        return CortexClient.builder()
            .withApiKey("your_api_key")
            .withEnvironment(Environment.PRODUCTION)
            .build();
    }
}

// Controller
import com.cortexplatform.sdk.CortexClient;
import com.cortexplatform.sdk.conversation.Conversation;
import com.cortexplatform.sdk.message.Message;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/chat")
public class ChatController {

    private final CortexClient cortexClient;

    @Autowired
    public ChatController(CortexClient cortexClient) {
        this.cortexClient = cortexClient;
    }

    @PostMapping("/conversations")
    public Conversation createConversation() {
        return cortexClient.conversations().create(
            new ConversationRequest.Builder().build()
        );
    }

    @PostMapping("/conversations/{conversationId}/messages")
    public Message createMessage(
        @PathVariable String conversationId,
        @RequestBody MessageRequest request
    ) {
        return cortexClient.messages().create(
            conversationId,
            new MessageRequest.Builder()
                .content(request.getContent())
                .role(Role.USER)
                .modality(Modality.TEXT)
                .build()
        );
    }

    @GetMapping("/conversations/{conversationId}/messages")
    public MessageListResult getMessages(@PathVariable String conversationId) {
        return cortexClient.messages().list(
            conversationId,
            new ListOptions.Builder().build()
        );
    }
}
```

### ASP.NET Core Integration

```csharp
// Program.cs
using CortexPlatform.SDK;
using CortexPlatform.SDK.AspNetCore;

var builder = WebApplication.CreateBuilder(args);

// Add Cortex services
builder.Services.AddCortexPlatform(options => {
    options.ApiKey = "your_api_key";
    options.Environment = Environment.Production;
});

var app = builder.Build();

// Controller
using Microsoft.AspNetCore.Mvc;
using CortexPlatform.SDK;
using CortexPlatform.SDK.Conversations;
using CortexPlatform.SDK.Messages;

[ApiController]
[Route("api/chat")]
public class ChatController : ControllerBase
{
    private readonly ICortexClient _cortexClient;

    public ChatController(ICortexClient cortexClient)
    {
        _cortexClient = cortexClient;
    }

    [HttpPost("conversations")]
    public async Task<IActionResult> CreateConversation()
    {
        var conversation = await _cortexClient.Conversations.CreateAsync(
            new ConversationRequest()
        );

        return Ok(conversation);
    }

    [HttpPost("conversations/{conversationId}/messages")]
    public async Task<IActionResult> CreateMessage(
        string conversationId,
        [FromBody] MessageRequestModel request)
    {
        var message = await _cortexClient.Messages.CreateAsync(
            conversationId,
            new MessageRequest
            {
                Content = request.Content,
                Role = Role.User,
                Modality = Modality.Text
            }
        );

        return Ok(message);
    }

    [HttpGet("conversations/{conversationId}/messages")]
    public async Task<IActionResult> GetMessages(string conversationId)
    {
        var result = await _cortexClient.Messages.ListAsync(
            conversationId,
            new ListOptions()
        );

        return Ok(result);
    }
}

// Request model
public class MessageRequestModel
{
    public string Content { get; set; }
}
```

## Sample Applications

For complete example applications, refer to:

- [JavaScript/TypeScript Examples](https://github.com/cortex-platform/cortex-js-examples)
- [Python Examples](https://github.com/cortex-platform/cortex-python-examples)
- [Java Examples](https://github.com/cortex-platform/cortex-java-examples)
- [C# Examples](https://github.com/cortex-platform/cortex-csharp-examples)

## Support

For SDK support, please contact:

- GitHub Issues: [https://github.com/cortex-platform/sdk/issues](https://github.com/cortex-platform/sdk/issues)
- Developer Forums: [https://developers.cortex-platform.example.com/forum](https://developers.cortex-platform.example.com/forum)
- Email: [sdk-support@cortex-platform.example.com](mailto:sdk-support@cortex-platform.example.com)
