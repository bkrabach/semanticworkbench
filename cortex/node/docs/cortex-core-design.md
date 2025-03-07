# Cortex Core MVP Design and Implementation Plan

## 1. System Overview

The Cortex Core MVP will implement a modular, extensible architecture that serves as the central orchestration engine for the Cortex Platform. This implementation will include all essential functionality required to coordinate user interactions, manage context, delegate specialized tasks, and integrate with external tools.

### Core Principles

- **Modularity**: All components are designed with clear boundaries and interfaces
- **Extensibility**: The system is built to support future enhancements and component replacements
- **Adaptive Intelligence**: Core decision-making adapts based on user context and needs
- **Integration Ready**: Standard protocols (primarily MCP) for external connections

## 2. Key Components

### 2.1 Session Manager

The Session Manager will be responsible for:

- User session creation, validation, and termination
- Session state persistence 
- Association of sessions with workspaces
- Session-specific configuration management

```typescript
interface SessionManager {
  // Create a new user session
  createSession(userId: string, config?: SessionConfig): Promise<Session>;
  
  // Retrieve an existing session
  getSession(sessionId: string): Promise<Session | null>;
  
  // Terminate an existing session
  terminateSession(sessionId: string): Promise<boolean>;
  
  // Validate if a session is active and valid
  validateSession(sessionId: string): Promise<boolean>;
  
  // Update session metadata or configuration
  updateSession(sessionId: string, updates: Partial<SessionConfig>): Promise<Session>;
}

interface Session {
  id: string;
  userId: string;
  createdAt: Date;
  lastActiveAt: Date;
  activeWorkspaceId: string;
  config: SessionConfig;
  metadata: Record<string, any>;
}

interface SessionConfig {
  timeoutMinutes: number;
  defaultWorkspaceId?: string;
  preferredModalities?: string[]; // e.g., ["chat", "voice"]
}
```

### 2.2 Dispatcher

The Dispatcher will:

- Route incoming requests to appropriate handlers
- Prioritize and queue requests when necessary
- Invoke domain experts for specialized tasks
- Coordinate between different processing pathways

```typescript
interface Dispatcher {
  // Register a handler for a specific request type
  registerHandler(requestType: string, handler: RequestHandler): void;
  
  // Dispatch an incoming request to the appropriate handler
  dispatch(request: Request): Promise<Response>;
  
  // Route a task to a domain expert
  delegateToExpert(expertType: string, task: Task): Promise<TaskResult>;
  
  // Cancel an in-progress request
  cancelRequest(requestId: string): Promise<boolean>;
}

interface RequestHandler {
  handleRequest(request: Request): Promise<Response>;
  canHandle(request: Request): boolean;
}

interface Request {
  id: string;
  type: string;
  sessionId: string;
  modality: string; // e.g., "chat", "voice", etc.
  content: any;
  metadata: Record<string, any>;
  timestamp: Date;
}

interface Response {
  requestId: string;
  status: "success" | "error" | "pending";
  content: any;
  timestamp: Date;
}
```

### 2.3 Context Manager

The Context Manager will:

- Interface with the memory system (initially a "whiteboard" implementation)
- Retrieve relevant context for processing requests
- Update the memory state with new information
- Maintain an in-memory cache of recent context for performance

```typescript
interface ContextManager {
  // Get context relevant to a specific query or task
  getContext(sessionId: string, workspaceId: string, query?: string): Promise<Context>;
  
  // Update the context with new information
  updateContext(sessionId: string, workspaceId: string, contextUpdate: ContextUpdate): Promise<void>;
  
  // Clear outdated or irrelevant context
  pruneContext(sessionId: string, workspaceId: string, olderThan?: Date): Promise<void>;
}

interface Context {
  messages: Message[];
  entities: Entity[];
  metadata: Record<string, any>;
  lastUpdated: Date;
}

interface ContextUpdate {
  addMessages?: Message[];
  removeMessageIds?: string[];
  addEntities?: Entity[];
  removeEntityIds?: string[];
  updateMetadata?: Record<string, any>;
}

interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: Date;
  metadata?: Record<string, any>;
}

interface Entity {
  id: string;
  type: string;
  name: string;
  properties: Record<string, any>;
}
```

### 2.4 Integration Hub

The Integration Hub will:

- Implement the MCP client/server protocol for external integrations
- Manage connections to external tools and services
- Route data between the core system and external components
- Handle protocol translation when necessary

```typescript
interface IntegrationHub {
  // Register a new external integration
  registerIntegration(integration: Integration): Promise<void>;
  
  // Get an integration by ID
  getIntegration(integrationId: string): Promise<Integration | null>;
  
  // Forward a request to an external integration
  forwardRequest(integrationId: string, request: any): Promise<any>;
  
  // Handle incoming requests from external integrations
  handleExternalRequest(integrationId: string, request: any): Promise<any>;
  
  // List all active integrations
  listIntegrations(): Promise<Integration[]>;
}

interface Integration {
  id: string;
  name: string;
  type: "vscode" | "m365" | "browser" | "other";
  connectionDetails: ConnectionDetails;
  capabilities: string[];
  status: "connected" | "disconnected" | "error";
  lastActive: Date;
}

interface ConnectionDetails {
  protocol: "mcp" | "rest" | "websocket";
  endpoint: string;
  authToken?: string;
  metadata?: Record<string, any>;
}
```

### 2.5 Workspace Manager

The Workspace Manager will:

- Create and manage workspaces for organizing user interactions
- Handle creation and retrieval of conversations within workspaces
- Transform raw activity logs into modality-specific conversation views
- Expose APIs for workspace and conversation management

```typescript
interface WorkspaceManager {
  // Create a new workspace
  createWorkspace(userId: string, name: string, config?: WorkspaceConfig): Promise<Workspace>;
  
  // Get workspace by ID
  getWorkspace(workspaceId: string): Promise<Workspace | null>;
  
  // List workspaces for a user
  listWorkspaces(userId: string): Promise<Workspace[]>;
  
  // Create a conversation in a workspace
  createConversation(workspaceId: string, modality: string, title?: string): Promise<Conversation>;
  
  // Get a conversation by ID
  getConversation(conversationId: string): Promise<Conversation | null>;
  
  // List conversations in a workspace
  listConversations(workspaceId: string, filter?: ConversationFilter): Promise<Conversation[]>;
  
  // Add an entry to a conversation
  addConversationEntry(conversationId: string, entry: ConversationEntry): Promise<void>;
}

interface Workspace {
  id: string;
  userId: string;
  name: string;
  createdAt: Date;
  lastActiveAt: Date;
  config: WorkspaceConfig;
  metadata: Record<string, any>;
}

interface WorkspaceConfig {
  defaultModality?: string;
  sharingEnabled: boolean;
  retentionDays: number;
}

interface Conversation {
  id: string;
  workspaceId: string;
  modality: string;
  title: string;
  createdAt: Date;
  lastActiveAt: Date;
  entries: ConversationEntry[];
  metadata: Record<string, any>;
}

interface ConversationEntry {
  id: string;
  type: "user" | "assistant" | "system";
  content: any;
  timestamp: Date;
  metadata?: Record<string, any>;
}

interface ConversationFilter {
  modality?: string;
  fromDate?: Date;
  toDate?: Date;
  searchText?: string;
}
```

### 2.6 Security Manager

The Security Manager will:

- Handle user authentication and authorization
- Manage API keys and access tokens
- Implement encryption for sensitive data
- Enforce access control policies

```typescript
interface SecurityManager {
  // Authenticate a user and create a session token
  authenticate(credentials: UserCredentials): Promise<AuthResult>;
  
  // Verify if a token is valid
  verifyToken(token: string): Promise<VerificationResult>;
  
  // Generate an API key for programmatic access
  generateApiKey(userId: string, scope: string[], expiry?: Date): Promise<ApiKey>;
  
  // Validate access permissions for a specific resource
  checkAccess(userId: string, resource: string, action: string): Promise<boolean>;
  
  // Encrypt sensitive data
  encrypt(data: string): Promise<string>;
  
  // Decrypt sensitive data
  decrypt(encryptedData: string): Promise<string>;
}

interface UserCredentials {
  type: "password" | "api_key" | "oauth" | "msal";
  identifier: string;
  secret?: string;
  provider?: string;
}

interface AuthResult {
  success: boolean;
  userId?: string;
  token?: string;
  expiresAt?: Date;
  error?: string;
}

interface VerificationResult {
  valid: boolean;
  userId?: string;
  scopes?: string[];
  error?: string;
}

interface ApiKey {
  key: string;
  userId: string;
  scopes: string[];
  createdAt: Date;
  expiresAt?: Date;
}
```

## 3. External Interfaces

### 3.1 Input/Output Modality Interface

The Cortex Core will expose a standard interface for all input/output modalities:

```typescript
interface ModalityInterface {
  // Register a new input modality
  registerInputModality(modalityType: string, handler: InputModalityHandler): void;
  
  // Register a new output modality
  registerOutputModality(modalityType: string, handler: OutputModalityHandler): void;
  
  // Process input from a specific modality
  processInput(modalityType: string, input: ModalityInput): Promise<void>;
  
  // Send output to a specific modality
  sendOutput(modalityType: string, output: ModalityOutput): Promise<void>;
  
  // List all registered modalities
  listModalities(): Promise<ModalityInfo[]>;
}

interface InputModalityHandler {
  handleInput(input: ModalityInput): Promise<void>;
  getCapabilities(): ModalityCapabilities;
}

interface OutputModalityHandler {
  handleOutput(output: ModalityOutput): Promise<void>;
  getCapabilities(): ModalityCapabilities;
}

interface ModalityInput {
  sessionId: string;
  content: any;
  metadata: Record<string, any>;
  timestamp: Date;
}

interface ModalityOutput {
  sessionId: string;
  content: any;
  metadata: Record<string, any>;
  priority: "high" | "normal" | "low";
}

interface ModalityCapabilities {
  supportedContentTypes: string[];
  supportsPrioritization: boolean;
  supportsInterruption: boolean;
  supportsMultipleDestinations: boolean;
}

interface ModalityInfo {
  type: string;
  direction: "input" | "output" | "both";
  capabilities: ModalityCapabilities;
  status: "active" | "inactive";
}
```

### 3.2 Memory System Interface

The Core will interact with the memory system through a standardized interface:

```typescript
interface MemorySystemInterface {
  // Initialize the memory system
  initialize(config: MemoryConfig): Promise<void>;
  
  // Store a memory item
  store(workspaceId: string, item: MemoryItem): Promise<string>;
  
  // Retrieve memory items based on a query
  retrieve(workspaceId: string, query: MemoryQuery): Promise<MemoryItem[]>;
  
  // Update an existing memory item
  update(workspaceId: string, itemId: string, updates: Partial<MemoryItem>): Promise<void>;
  
  // Delete a memory item
  delete(workspaceId: string, itemId: string): Promise<void>;
  
  // Generate a synthetic/enriched context from raw memory
  synthesizeContext(workspaceId: string, query: MemoryQuery): Promise<SynthesizedMemory>;
}

interface MemoryConfig {
  storageType: "in_memory" | "persistent";
  retentionPolicy?: RetentionPolicy;
  encryptionEnabled: boolean;
}

interface MemoryItem {
  id?: string;
  type: "message" | "entity" | "file" | "event";
  content: any;
  metadata: Record<string, any>;
  timestamp: Date;
  expiresAt?: Date;
}

interface MemoryQuery {
  types?: string[];
  fromTimestamp?: Date;
  toTimestamp?: Date;
  contentQuery?: string;
  metadataFilters?: Record<string, any>;
  limit?: number;
  includeExpired?: boolean;
}

interface SynthesizedMemory {
  rawItems: MemoryItem[];
  summary: string;
  entities: Record<string, any>;
  relevanceScore: number;
}

interface RetentionPolicy {
  defaultTtlDays: number;
  typeSpecificTtl?: Record<string, number>; // type -> days
  maxItems?: number;
}
```

### 3.3 Domain Expert Interface

For delegating specialized tasks to domain expert entities:

```typescript
interface DomainExpertInterface {
  // Register a new domain expert
  registerExpert(expertType: string, handler: ExpertHandler): void;
  
  // Delegate a task to a domain expert
  delegateTask(expertType: string, task: ExpertTask): Promise<TaskId>;
  
  // Check the status of a delegated task
  checkTaskStatus(taskId: TaskId): Promise<TaskStatus>;
  
  // Get the result of a completed task
  getTaskResult(taskId: TaskId): Promise<ExpertTaskResult>;
  
  // Cancel an in-progress task
  cancelTask(taskId: TaskId): Promise<boolean>;
  
  // List all registered domain experts
  listExperts(): Promise<ExpertInfo[]>;
}

interface ExpertHandler {
  handleTask(task: ExpertTask): Promise<TaskId>;
  checkStatus(taskId: TaskId): Promise<TaskStatus>;
  getResult(taskId: TaskId): Promise<ExpertTaskResult>;
  cancelTask(taskId: TaskId): Promise<boolean>;
  getCapabilities(): ExpertCapabilities;
}

type TaskId = string;

interface ExpertTask {
  id?: TaskId;
  type: string;
  content: any;
  context?: any;
  constraints?: TaskConstraints;
  metadata: Record<string, any>;
}

interface TaskConstraints {
  deadline?: Date;
  maxTokens?: number;
  priorityLevel?: "high" | "normal" | "low";
  maxRetries?: number;
}

interface TaskStatus {
  id: TaskId;
  state: "queued" | "processing" | "completed" | "failed" | "cancelled";
  progress?: number; // 0-100
  estimatedCompletionTime?: Date;
  statusMessage?: string;
}

interface ExpertTaskResult {
  taskId: TaskId;
  success: boolean;
  result?: any;
  error?: string;
  metrics?: Record<string, any>;
}

interface ExpertCapabilities {
  supportedTaskTypes: string[];
  supportsAsyncTasks: boolean;
  supportsCancellation: boolean;
  supportsProgress: boolean;
  maxConcurrentTasks?: number;
}

interface ExpertInfo {
  type: string;
  name: string;
  capabilities: ExpertCapabilities;
  status: "available" | "busy" | "offline";
}
```

### 3.4 MCP Integration Interface

To connect with external tools using the Model Context Protocol:

```typescript
interface MCPIntegrationInterface {
  // Initialize the MCP server
  initializeServer(config: MCPServerConfig): Promise<void>;
  
  // Initialize an MCP client to connect to external services
  initializeClient(connectionDetails: MCPConnectionDetails): Promise<MCPClientId>;
  
  // Send a request to an MCP client
  sendClientRequest(clientId: MCPClientId, request: MCPRequest): Promise<MCPResponse>;
  
  // Handle a request from an MCP client
  handleServerRequest(request: MCPRequest): Promise<MCPResponse>;
  
  // Register a handler for a specific MCP method
  registerMethodHandler(method: string, handler: MCPMethodHandler): void;
  
  // Send a notification to an MCP client
  sendNotification(clientId: MCPClientId, notification: MCPNotification): Promise<void>;
}

type MCPClientId = string;

interface MCPServerConfig {
  name: string;
  version: string;
  capabilities: Record<string, any>;
  transportTypes: ("stdio" | "sse" | "websocket")[];
}

interface MCPConnectionDetails {
  endpoint: string;
  protocol: "stdio" | "sse" | "websocket";
  authToken?: string;
  clientName: string;
  clientVersion: string;
}

interface MCPRequest {
  method: string;
  params?: any;
  id: string | number;
}

interface MCPResponse {
  result?: any;
  error?: MCPError;
  id: string | number;
}

interface MCPError {
  code: number;
  message: string;
  data?: any;
}

interface MCPNotification {
  method: string;
  params?: any;
}

interface MCPMethodHandler {
  handleMethod(params: any): Promise<any>;
}
```

## 4. Implementation Approach

### 4.1 Technology Stack

For the Cortex Core MVP, we recommend the following technology stack:

- **Backend**: Node.js with TypeScript
- **API Layer**: Express.js or Fastify
- **Real-time Communication**: Server-Sent Events (SSE) for stream responses
- **Database**: PostgreSQL for persistent storage
- **Cache**: Redis for performance optimization
- **Authentication**: JWT tokens with Microsoft Authentication Library (MSAL) integration

### 4.2 Implementation Phases

#### Phase 1: Core Infrastructure (2 weeks)

- Set up project structure and build system
- Implement basic versions of all six core components
- Create stub implementations of all external interfaces
- Build API endpoints for core functionality
- Implement the RESTful API layer
- Set up basic authentication

#### Phase 2: Memory System Integration (1 week)

- Build the "whiteboard" memory implementation
- Implement memory retrieval and update flows
- Create the memory synthesis process
- Connect memory to input processing pipeline

#### Phase 3: Modality and Workspace Support (2 weeks)

- Implement the workspace and conversation management
- Build input/output modality registration framework
- Implement basic chat and voice modality handlers
- Create user session management
- Implement modality-specific transformation logic

#### Phase 4: MCP Integration (2 weeks)

- Implement MCP client/server protocol
- Build resource listing and access mechanisms
- Create the tool invocation flow
- Implement the notification system
- Build support for SSE-based communication

#### Phase 5: Domain Expert Framework (1 week)

- Create the domain expert registration system
- Implement task delegation workflow
- Build the task status tracking mechanism
- Create the expert result handling flow
- Implement guided conversation protocol

#### Phase 6: Testing, Documentation & Deployment (2 weeks)

- Comprehensive testing of all components
- Documentation of all interfaces and APIs
- Create developer guides for building extensions
- Deploy MVP to staging environment
- Final integration testing

### 4.3 Database Schema

The core database schema should include these primary tables:

1. `users` - User accounts and authentication
2. `sessions` - Active user sessions
3. `workspaces` - User workspaces
4. `conversations` - Conversations within workspaces
5. `messages` - Individual messages within conversations
6. `memory_items` - Persistent memory storage
7. `entities` - Named entities recognized in conversations
8. `domain_expert_tasks` - Task delegation records
9. `integrations` - External integration connections

### 4.4 API Endpoints

The Cortex Core will expose these primary RESTful API endpoints:

#### Authentication
- `POST /auth/login` - Authenticate a user
- `POST /auth/refresh` - Refresh an authentication token
- `POST /auth/logout` - End a user session

#### Workspaces
- `GET /workspaces` - List user workspaces
- `POST /workspaces` - Create a new workspace
- `GET /workspaces/:id` - Get workspace details
- `PUT /workspaces/:id` - Update workspace
- `DELETE /workspaces/:id` - Delete workspace

#### Conversations
- `GET /workspaces/:id/conversations` - List conversations in workspace
- `POST /workspaces/:id/conversations` - Create a new conversation
- `GET /conversations/:id` - Get conversation details
- `POST /conversations/:id/messages` - Add message to conversation
- `GET /conversations/:id/messages` - Get messages in conversation

#### Input/Output
- `POST /input/:modality` - Send input through a specific modality
- `GET /output/:modality/stream` - Stream outputs for a specific modality (SSE)

#### Domain Experts
- `GET /experts` - List available domain experts
- `POST /experts/:type/tasks` - Create a task for domain expert
- `GET /experts/tasks/:id` - Get task status and results

#### Integrations
- `GET /integrations` - List connected integrations
- `POST /integrations` - Register a new integration
- `DELETE /integrations/:id` - Remove an integration

#### MCP Endpoint
- `POST /mcp` - MCP message endpoint for HTTP transport
- `GET /mcp/events` - SSE endpoint for MCP server-sent events

## 5. Test Strategy

### 5.1 Unit Testing

Each component should have comprehensive unit tests covering:
- Core functionality
- Edge cases
- Error handling
- Interface compliance

### 5.2 Integration Testing

Test interactions between components:
- Memory system integration
- Modality handler interactions
- Domain expert task delegation
- MCP protocol implementation

### 5.3 System Testing

End-to-end tests of complete flows:
- User session creation and management
- Input processing through to output generation
- Task delegation and result handling
- Workspace and conversation management

### 5.4 Performance Testing

- Response time under different loads
- Concurrent user session handling
- Memory usage and optimization
- Database query performance

## 6. Future Enhancements (Post-MVP)

After the MVP is operational, these enhancements should be prioritized:

1. **Advanced JAKE Memory Integration** - Replace the whiteboard implementation with full JAKE
2. **Enhanced Cognition System** - Implement more sophisticated decision-making and planning
3. **Additional Domain Experts** - Create code assistant and deep research experts
4. **Expanded Modality Support** - Add canvas, dashboard, and notification modalities
5. **Security Enhancements** - Add more authentication options and fine-grained permissions
6. **Performance Optimizations** - Caching, query optimization, and scaling improvements
7. **Analytics and Monitoring** - Add usage tracking and system health monitoring

## 7. Resources Required

### 7.1 Development Team

- 1 Technical Lead
- 2-3 Backend Developers
- 1 DevOps Engineer
- 1 QA Engineer

### 7.2 Infrastructure

- Development environment
- Staging environment
- CI/CD pipeline
- Monitoring and logging infrastructure

## 8. Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Integration complexity with external systems | High | Medium | Create well-defined interfaces with thorough documentation |
| Performance issues with memory management | High | Medium | Implement efficient caching and optimization strategies |
| Security vulnerabilities | High | Low | Regular security audits and adherence to best practices |
| Scalability challenges | Medium | Medium | Design with horizontal scaling in mind from the beginning |
| API compatibility issues | Medium | Medium | Version all APIs and ensure backward compatibility |

## 9. Success Criteria

The MVP will be considered successful when:

1. All core components are fully implemented and operational
2. External interfaces are well-defined and tested
3. Basic modalities (chat, voice) are functional
4. The system can maintain context across interactions
5. Domain expert delegation framework is operational
6. MCP integration is working for at least one external tool
7. Performance meets acceptable thresholds (< 500ms response time)
8. Documentation is complete for all interfaces

## 10. Conclusion

This design document outlines a comprehensive plan to build a Minimum Viable Product of the Cortex Core that fulfills the essential requirements while enabling parallel development of surrounding components. By focusing on modular design, clear interfaces, and extensibility, this implementation will provide a solid foundation for the Cortex Platform that can evolve over time with additional features and capabilities.

The phased approach outlined here allows for incremental development and testing, reducing risks and allowing for early feedback. By implementing the core functionality first and then progressively adding support for memory, modalities, experts, and integrations, we can ensure a stable and reliable system that meets the platform's goals.
