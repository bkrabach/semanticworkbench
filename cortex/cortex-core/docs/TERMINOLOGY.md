# Cortex Core Terminology Guide

This document provides a definitive reference for terminology used throughout the Cortex Core codebase and documentation. It ensures consistent terminology across all components and helps new developers understand the specialized vocabulary used in the project.

## Core Concepts

### Platform Components

| Term | Definition | Implementation |
|------|------------|---------------|
| **Cortex Core** | Central orchestration engine for the Cortex Platform | Main FastAPI application |
| **Cortex Router** | Component that processes inputs and makes routing decisions | `app/components/cortex_router.py` |
| **Session Manager** | Handles user sessions and authentication | Authentication components |
| **Context Manager** | Manages unified context across interactions | Memory system integration |
| **Integration Hub** | Manages connections to Domain Expert services | `app/components/integration_hub.py` |
| **Workspace Manager** | Manages workspaces and their associated resources | Workspace service and repositories |
| **Security Manager** | Handles authentication, authorization, and encryption | Auth components and token handling |

### Domain Concepts

| Term | Definition | Implementation |
|------|------------|---------------|
| **Workspace** | Container for conversations and resources | Database and domain models |
| **Conversation** | Thread of interactions between users and AI | Database and domain models |
| **Message** | Individual interaction within a conversation | Database and domain models |
| **Channel** | Input/output communication path | Router interfaces |
| **Modality** | Form of input/output (chat, voice, canvas, etc.) | Channel type enum |
| **Memory Item** | Stored piece of context for later retrieval | Memory system models |
| **Resource** | External asset that can be accessed by the system | Database and domain models |

### Architectural Patterns

| Term | Definition | Implementation |
|------|------------|---------------|
| **Repository Pattern** | Abstraction layer for data access | Repository classes |
| **Service Layer** | Contains business logic between API and repositories | Service classes |
| **Domain Model** | Represents core business entities | Pydantic models |
| **API Model** | Represents HTTP request/response structures | Pydantic models |
| **Database Model** | Represents database schema | SQLAlchemy models |
| **Event System** | Publish/subscribe mechanism for decoupled communication | Event system implementation |
| **Dependency Injection** | Providing dependencies to components | FastAPI dependency system |

### Integration and Communication

| Term | Definition | Implementation |
|------|------------|---------------|
| **Domain Expert Entity** | Specialized autonomous module with deep expertise | MCP integration |
| **Model Context Protocol (MCP)** | Standardized protocol for service communication | MCP client implementation |
| **Server-Sent Events (SSE)** | Real-time, server-to-client communication | SSE implementation |
| **LLM Service** | Interface to language model providers | LLM service implementation |
| **Input Receiver** | Component that accepts input from external sources | Input receiver interfaces |
| **Output Publisher** | Component that sends output to external destinations | Output publisher interfaces |

### Memory System

| Term | Definition | Implementation |
|------|------------|---------------|
| **Whiteboard Memory** | Simple database-backed memory implementation | Current memory implementation |
| **JAKE Memory** | Advanced vector-based memory (planned) | Future implementation |
| **Memory Query** | Structured query for retrieving memory items | Memory system interfaces |
| **Synthesized Memory** | Processed and enhanced memory context | Memory system interfaces |
| **Retention Policy** | Rules for how long memory items are kept | Memory configuration |

## Mapping Vision to Implementation

The following table maps terms from the vision documents to their current implementation:

| Vision Term | Implementation Term | Status |
|-------------|---------------------|--------|
| **Cortex Core** | Cortex Core main application | Implemented |
| **Memory System (JAKE)** | Whiteboard Memory | Partial (JAKE planned) |
| **Cognition System** | Context Manager | Partial |
| **Domain Expert Entities** | MCP Integration Framework | Partial |
| **Multi-Modal I/O** | Channel Types | Partial |
| **Central AI Core** | CortexRouter + LLM Service | Implemented |
| **Adaptive Ecosystem** | Integration Hub | Partial |

## Technical Terms and Abbreviations

| Term/Abbreviation | Definition |
|-------------------|------------|
| **ADR** | Architecture Decision Record |
| **API** | Application Programming Interface |
| **CRUD** | Create, Read, Update, Delete |
| **DTO** | Data Transfer Object |
| **JWT** | JSON Web Token |
| **LLM** | Large Language Model |
| **MCP** | Model Context Protocol |
| **ORM** | Object-Relational Mapping |
| **SSE** | Server-Sent Events |
| **TTL** | Time To Live |
| **UUID** | Universally Unique Identifier |

## Action Types

| Action Type | Definition |
|-------------|------------|
| **RESPOND** | Generate an immediate response |
| **PROCESS** | Process the message with specialized logic |
| **DELEGATE** | Delegate to a domain expert |
| **IGNORE** | Take no action |
| **CLARIFY** | Ask for clarification |
| **SEARCH** | Search for information |
| **ROUTE** | Route to a specific handler |

## Event Types

| Event Type | Definition |
|------------|------------|
| **connect** | Initial connection established |
| **connection_confirmed** | Connection confirmation |
| **heartbeat** | Periodic heartbeat to keep connection alive |
| **message_received** | New message received in a conversation |
| **typing_indicator** | Typing status updates |
| **status_update** | Status update for a conversation or workspace |

## Channel Types

| Channel Type | Definition |
|--------------|------------|
| **CONVERSATION** | Text chat modality |
| **VOICE** | Voice interaction modality |
| **CANVAS** | Visual workspace modality |
| **APP** | Application UI modality |
| **WEBHOOK** | External webhook modality |
| **API** | API endpoint modality |
| **EMAIL** | Email communication modality |
| **SMS** | SMS/text message modality |
| **NOTIFICATION** | System notification modality |
| **CLI** | Command line interface modality |
| **CUSTOM** | Custom modality type |

## SSE Channel Types

| SSE Channel Type | Definition |
|------------------|------------|
| **global** | System-wide events |
| **user** | User-specific events |
| **workspace** | Workspace-specific events |
| **conversation** | Conversation-specific events |

## Memory Item Types

| Memory Item Type | Definition |
|------------------|------------|
| **message** | Conversation messages with role, content, and metadata |
| **entity** | Named entities extracted from conversations |
| **file** | Document or file references with content and metadata |
| **event** | System or user-generated events with timestamps |

## Using Consistent Terminology

When writing code or documentation for Cortex Core:

1. **Be Consistent**: Use the terms from this guide consistently
2. **Be Precise**: Use the exact term that matches the concept
3. **Be Clear**: Avoid abbreviations when clarity is needed
4. **Maintain Mappings**: Maintain the mapping between vision and implementation

## Related Documents

- [ARCHITECTURE.md](ARCHITECTURE.md): Overall system architecture
- [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md): Current implementation status
- [DOMAIN_EXPERTS.md](DOMAIN_EXPERTS.md): Domain expert entities documentation