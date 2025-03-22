# Cortex Core MVP – Mini-Project Breakdown

This breakdown divides the Cortex Core MVP implementation into focused mini-projects. Each mini-project is scoped for **ruthless simplicity**, clear separation of concerns, and minimal interfaces. They leverage third-party libraries directly (Auth0, FastMCP, Pydantic & Pydantic-AI) without unnecessary abstraction. The goal is to let each component be built and reasoned about independently, while maintaining strong architectural integrity with minimal “ceremony.”

## 1. Project Structure and Initial Setup

**Scope:** Scaffold the project with a clean, minimal structure that reflects the architecture. This sets up an organized codebase without implementing functionality yet.

- **Create the FastAPI Project:** Initialize a FastAPI application (e.g., `app/main.py`) with a simple health-check route to verify setup.
- **Organize Modules:** Establish a package layout for key concerns:
  - `api/` for API route handlers (submodules like `auth.py`, `input.py`, `output.py`, `config.py`).
  - `core/` for internal logic (event handling, orchestration, integrations).
  - `models/` for data models (perhaps sub-files for domain vs API schemas).
  - `backend/` for auxiliary services (Memory and Cognition microservices).
  - `utils/` (optional) for small utilities (e.g., auth helpers).
- **Separation of Concerns:** Create empty classes/functions as placeholders for major components (e.g., an `EventBus` class, a `ResponseHandler` function) so that later mini-projects can work in parallel with clear interfaces. Document these interfaces (via docstrings or comments) to set expectations (for example, note that `EventBus.publish(event)` will broadcast to subscribers).
- **Minimal Dependencies:** Aside from FastAPI (and Uvicorn to run), do not add other dependencies yet. This step is about structure, not functionality. Keep it lean – code not written yet can’t add complexity.

## 2. Domain and API Data Models

**Scope:** Define the data models using Pydantic for both internal domain representation and external API schemas. These models enforce clear contracts and type safety across components with minimal boilerplate.

- **Domain Models:** Create Pydantic models for core entities such as `User`, `Workspace`, `Conversation`, and `Message`. Include only essential fields:
  - _User:_ e.g., `id`, `name`, `email`.
  - _Workspace:_ `id`, `owner_id` (user), `name`.
  - _Conversation:_ `id`, `workspace_id`, maybe a `title`.
  - _Message:_ `id`, `conversation_id`, `sender` (user or assistant), `content`, `timestamp`.
    Ensure required fields are non-nullable by default for type safety. These domain models will be used by internal logic and services.
- **API Schemas:** Define Pydantic models for request/response bodies where appropriate:
  - Auth requests (e.g., `LoginRequest` with `email` and `password` if needed).
  - Auth responses or user info (e.g., `AuthUser` with token or user profile).
  - Configuration endpoints (e.g., `WorkspaceCreateRequest`, `ConversationCreateRequest`, and their responses).
  - If the input message format needs validation, define an `InputMessage` schema with fields like `content` (and possibly `conversation_id` if multi-conversation is supported). For simplicity, we might treat all input as a basic `{ "content": "...", "conversation_id": "..." }` shape.
- **Use Pydantic Directly:** Avoid any custom validation logic that Pydantic can handle. Rely on Pydantic’s parsing for JSON requests and its automatic error reporting for invalid data. This keeps interfaces minimal and clear.
- **Future LLM Output Schema:** Anticipate structured LLM outputs using **pydantic-ai**. Define Pydantic models for expected LLM outputs:
  - For example, a `ToolRequest` model with fields like `tool: str` and `args: dict`, and a `FinalAnswer` model with field `answer: str`. These will help parse and validate the AI’s response format in the orchestration step. Defining them now (or in the Response Handler step) ensures the format between the LLM and the orchestrator is explicit and easily validated.

## 3. Authentication & Authorization (Auth0 Integration)

**Scope:** Implement the authentication layer using Auth0 (JWT verification). This provides secure endpoints with minimal custom code by leveraging standard libraries.

- **JWT Verification:** Use Auth0’s recommended approach to verify JWTs. Prefer a direct library solution over writing custom JWT parsing:
  - Use a library like **python-jose** (JOSE) or **authlib** to handle JWT decoding and signature verification. For Auth0, set up the JWKS (JSON Web Key Set) retrieval using their domain (e.g., via JOSE’s `PyJWKClient` if using RS256 tokens).
  - In development mode, if accessing Auth0 isn’t practical, allow using a hard-coded secret and HS256 tokens for simplicity. Clearly comment this as a dev-only shortcut.
- **Auth Utility Function/Dependency:** Implement a FastAPI dependency `get_current_user` that:
  - Validates the `Authorization: Bearer <token>` from the request header.
  - Decodes the JWT, verifies signature and expiration, and returns a simple user model or dict (e.g., `{"user_id": ..., "email": ...}`) to the endpoint.
  - If validation fails, it should raise an HTTP 401 Unauthorized. Use FastAPI’s HTTPException for brevity.
- **Minimal Interface:** Do not create a complex auth service or multiple layers of abstraction. A single utility function or small `Auth0Verifier` class is enough. It should have a clear interface (take a token and return user info or raise error).
- **Auth Endpoints (Optional Login):** If implementing a login endpoint for testing:
  - Keep it simple: Accept a dummy username/password, verify against a hard-coded value or stub, and return a JWT (signed with the dev secret or by calling Auth0’s API if feasible). This allows manual testing of authenticated flows.
  - This endpoint can be very basic since Auth0 is typically responsible for authentication flows; our focus is verifying tokens, not managing users.

## 4. API Endpoints (Input, Output, Config, etc.)

**Scope:** Develop the FastAPI endpoints that form the external interface of Cortex Core. Each endpoint should be minimal, primarily handling request validation, invoking the right internal service or publishing an event, and returning a response. Business logic should be delegated to core components.

- **Setup Routers:** Use FastAPI’s APIRouter to group related endpoints (e.g., `auth_router`, `chat_router`, `config_router`) to keep the code organized and concerns separated. Include these routers in the main app.
- **POST `/input` (Send Message):** Protected endpoint (requires JWT via `get_current_user`).
  - Accept a JSON payload for the user’s message (use the `InputMessage` Pydantic model if defined).
  - Determine the conversation context: if a conversation ID is provided use it; otherwise use a default conversation for that user (to keep MVP assumptions simple).
  - Invoke the core message processing by publishing an event to the Event Bus (e.g., an event dict with type `"input"`, the message content, user info, and conversation id). This fire-and-forget publish decouples the HTTP request from the processing.
  - Also call the Memory service immediately to store the message (so it’s saved even if no response yet). This can be done via the MCP client (see later) but within the request handler to ensure durability of the user’s message. Keep it as a simple one-line call (no waiting for response beyond perhaps an ack).
  - Return a success acknowledgement (e.g., HTTP 202 Accepted or 200 OK with a simple JSON `{"status": "received"}`). The actual response will come through the SSE stream.
- **GET `/output/stream` (Receive Streamed Response):** Protected endpoint that upgrades to a Server-Sent Events stream.
  - Use `get_current_user` to validate the token. Optionally accept a conversation ID query param (again, default to the single conversation if not provided).
  - Upon client connect, subscribe to the Event Bus for output events relevant to that user (and conversation). Likely, create an asyncio Queue or similar subscriber channel via the EventBus component.
  - Use FastAPI/Starlette’s StreamingResponse or a custom EventSourceResponse to continuously yield events from the queue. Each event could be sent as a line of text or JSON encoded (keeping to SSE format with `data: ...` lines).
  - Ensure the interface is minimal: no complex transformation of events, just take what the core publishes and stream it out. Also handle heartbeat or ping events if needed to keep connection alive (could be as simple as sending a comment every X seconds).
  - Make sure to disconnect properly: if the client disconnects, unsubscribe from the Event Bus to avoid leaking queues.
- **Auth Endpoints:**
  - `POST /auth/login`: As discussed, this may be a stub for testing. Only include it if needed for obtaining tokens easily in development.
  - `GET /auth/verify`: A simple protected endpoint that returns the current user info (proves that the auth token is working). This helps in testing authentication quickly.
- **Config Endpoints (Workspaces & Conversations):**
  - `POST /config/workspaces`: Create a new workspace (e.g., with a name). For MVP, store it in memory (maybe a global dict or a simple repository object). Associate it with the current user. Return the created workspace data.
  - `GET /config/workspaces`: List workspaces for the current user from the in-memory store.
  - `POST /config/conversations`: Create a new conversation under a given workspace (or default workspace). Generate an ID, store minimal info (like title or empty until first message).
  - `GET /config/conversations`: List conversations for a given workspace.
    These endpoints allow a frontend to manage contexts but are kept extremely simple (no database, just ephemeral storage). They demonstrate separation of this concern from the main chat logic.
- **Keep Logic Out of Endpoints:** The endpoints should not implement complex logic themselves. They should delegate: e.g., publishing to EventBus, calling memory client, etc. This ensures that each part (auth, event bus, services) can be developed and tested in isolation.

## 5. In-Memory Event Bus

**Scope:** Implement a lightweight in-memory event bus for decoupling producers and consumers of events within the core. This enables asynchronous communication (user input → background processing → output to SSE) without tying those components directly together. The design should be minimal: essentially a publish-subscribe mechanism using asyncio queues.

- **Event Bus Class:** Create an `EventBus` class (e.g., in `core/event_bus.py`) with a clear, minimal interface:
  - `subscribe(filter_criteria) -> Queue`: Allows a consumer to subscribe to certain events. For MVP, the filter could be based on user (and conversation) so each SSE client only receives their own messages. Implement by creating an `asyncio.Queue` for the subscriber. Store the queue along with the filter criteria in the EventBus.
  - `publish(event: dict)`: Puts an event into all queues whose filter criteria match the event. Event can be a simple dict or object with fields like `type` (e.g., "input" or "output"), `user_id`, `conversation_id`, and `data` (the content or payload). Keep this schema minimal and document it for consistency.
- **Simplicity in Implementation:** Use basic Python data structures. For example, maintain a list of subscribers, where each subscriber has a queue and perhaps a tuple of `(user_id, conversation_id)` it is interested in. When publishing, iterate over subscribers and put the event into those that match (for matching, user must match, and if conversation is specified, match that too). This avoids any complex topic naming or external brokers.
- **No Persistence:** The EventBus should not persist events. If no consumer is listening, events can be dropped. This is acceptable in MVP because the pattern is that an output event is only published when an SSE listener is expected to be present. Document this behavior clearly.
- **Threading/Async:** Ensure the EventBus operations are asyncio-friendly since FastAPI is async. The `subscribe` can simply provide an `asyncio.Queue` and returning events will be via `await queue.get()`. Because everything runs in the same event loop (single process), we don’t need locks or cross-thread coordination.
- **Integration:** Make the EventBus instance globally accessible but not as a hidden global if possible:
  - One approach: initialize `event_bus = EventBus()` in a module that can be imported where needed (or attach it to `app.state` in FastAPI).
  - This allows the `/input` endpoint handler to call `event_bus.publish(...)` and the ResponseHandler to call `event_bus.subscribe(...)` easily. Keep interface usage consistent.
- **Minimal Error Handling:** For MVP, the EventBus can assume proper usage (e.g., subscribers will call `get()` and not overflow their queues drastically). Add basic logging if an event is published with no subscribers, but otherwise avoid over-engineering (no need for backpressure handling at this stage).

## 6. MCP Client Integration for Services

**Scope:** Integrate the **FastMCP** SDK to allow Cortex Core to communicate with the Memory and Cognition services. The goal is to use the library as directly as possible, creating minimal functions or classes to invoke remote procedures on the services.

- **FastMCP Setup:** Install and import the FastMCP library. Create a small utility in `core/mcp_client.py` to manage connections:
  - For MVP, a simple approach is to establish an MCP client connection to each service (Memory, Cognition) at startup. For example, use `fastmcp.Connection` or similar to connect to the service’s URL/port. If FastMCP provides an async connect, call it during app startup (e.g., in a startup event or before launching the server).
  - Alternatively, lazy-connect on first use: attempt the call, and if the connection isn’t established, initiate it then. This reduces startup complexity but adds a bit of logic on call—keep it straightforward with a flag or simple check.
- **Service Client Functions:** Define clear, direct methods to call the services:
  - e.g., `memory_client.store_message(user_id, conversation_id, content)` which internally does something like `await memory_conn.call("store_message", user_id, conversation_id, content)` via the MCP SDK.
  - Similarly, `cognition_client.get_context(user_id, conversation_id)` to call the cognition service’s context retrieval function.
    These methods are thin wrappers or even just references to the MCP calls, existing only to provide a semantic interface to the rest of the core. Avoid adding any logic beyond packaging arguments and making the call.
- **Direct Usage of SDK:** Do not wrap the MCP client in additional abstraction layers (no custom pub/sub or queue beyond what’s needed). Rely on the FastMCP library’s patterns for sending requests and receiving responses or events. If the library supports streaming responses (for SSE), make use of it directly. If not needed (the services might return data in one go), just await the call result.
- **Error Handling:** Let exceptions bubble up for now or log them. For instance, if the memory service call fails, log it and let the orchestrator decide what to do (maybe proceed without memory). Avoid complex retry or fallback logic in the MVP. We trust the service to be available; if it’s not, failing fast is acceptable during development.
- **Configuration:** Use straightforward configuration for service URLs/ports (maybe read from environment or constants). E.g., `MEMORY_SERVICE_URL = "http://localhost:9100"`. Keep these in a config section or at the top of the module for easy adjustment.
- **Testing Consideration:** Ensure these client calls are easy to stub or mock. For example, if an assistant wants to test the ResponseHandler without running actual services, we might later swap out these calls with dummy functions. By keeping the interface minimal (like a simple function call per service action), such stubbing is trivial.

## 7. Memory & Cognition Services (MCP Servers)

**Scope:** Implement the Memory and Cognition backend services in a minimal fashion. These are external to Cortex Core (conceptually microservices), but for MVP they can be simple Python modules using FastMCP’s server capabilities or even FastAPI. The priority is to follow the **separation of concerns**: these services handle their domain logic (storing messages, retrieving context) independently, exposing a clear interface to the core via MCP.

- **Memory Service (MCP Tool Server):** Develop `backend/memory_service.py` (or a small package):
  - Use FastMCP’s server decorators (if available, e.g., `@mcp.tool`) to define a function like `store_message(user_id, conversation_id, content)` that appends the message to an in-memory store. Also possibly a `get_history(user_id, conversation_id, limit)` that returns recent messages for context.
  - The in-memory storage can be a module-level dictionary or object: e.g., `messages_store = {user_id: {conversation_id: [list_of_messages]}}`. Keep it simple with basic append and retrieve operations. No database or file persistence; data resets on each run (acceptable for MVP).
  - Ensure the service runs, listening on a port (e.g., 9000 or 9100). You can use `mcp.run("MemoryService", port=9000)` if the SDK supports it, or wrap it in a FastAPI app if needed, but avoid over-complicating. The focus is the function logic, not the web framework.
  - Keep logic minimal: no advanced search or vector database, just store and fetch. For now, assume a single default conversation per user unless conversation_id is provided (consistent with Core’s assumption). If conversation_id is not used, treat everything as one thread for that user.
- **Cognition Service:** Develop `backend/cognition_service.py` similarly:
  - Provide a function like `get_context(user_id, conversation_id)` that returns a summary or relevant context for the conversation. Since implementing real NLP summarization is out of scope for MVP, this can be as basic as retrieving the last few messages via the Memory service and concatenating them, or a stubbed response.
  - If demonstrating service-to-service call: the Cognition service can itself be an MCP client to Memory (calling `get_history`). This would show chaining, but it’s also fine to have Cognition use a simpler approach (or even maintain its own view of memory if passed in). For ruthless simplicity, you might skip cross-service calls and just have Cognition return a placeholder string like “(Context summary not implemented)” or the latest user message as context.
  - The main point is to have a callable endpoint so that Cortex Core’s MCP client can request `get_context` and get some result (even if trivial). This keeps the pattern intact.
- **Running the Services:** To maintain **architectural integrity**, ideally run Memory and Cognition as separate processes (their own FastMCP servers). For development convenience, you may:
  - Run each via a simple `if __name__ == "__main__":` block that starts the MCP service (on distinct ports). This allows launching them easily (e.g., `python backend/memory_service.py`).
  - Alternatively, during Core startup, spawn these services in background threads or subprocesses. This can simplify running the entire system (one command starts everything). If you do this, keep it clearly separated in code (so that in production they could be real separate services). For example, call `subprocess.Popen(["python", "backend/memory_service.py"])` on startup if needed.
  - Document any dev-time shortcuts clearly. The MVP should be easy to run, but not deviate from the intended architecture of separate components.
- **Minimal Error Handling:** Within these services, implement basic try/except around logic to avoid crashing on bad input, and log errors to console. They can trust the core to send valid data. No need for complex validation beyond maybe ensuring required fields exist (which Pydantic models from core should ensure).
- **Keep Them Decoupled:** These services do not interact with each other except via the core (or a conscious call from Cognition to Memory if chosen). They should not depend on core internals. This isolation ensures changes in core or other services don’t ripple here (and vice versa). Each service can be worked on independently as long as the MCP interface contract is met.

## 8. LLM Response Orchestrator (Response Handler)

**Scope:** Implement the core’s background processor that waits for input events and produces outputs (the assistant’s replies, possibly using tools). This is the heart of Cortex Core’s logic. It should orchestrate calls to the Memory and Cognition services and the LLM, applying the **pydantic-ai** structured output approach to decide if the LLM needs to use a tool or can answer directly. The design must remain as straightforward as possible: a linear sequence for handling each event, no extra abstraction layers.

- **Background Task Setup:** In the FastAPI app startup, launch the response handler as an **async task** (e.g., `asyncio.create_task(response_handler())`). The response handler function should subscribe to the EventBus for `"input"` events (filtered by appropriate criteria, or subscribe to all inputs and handle routing internally).
- **Event Loop:** Implement the handler loop to continually process events:
  ```python
  async def response_handler():
      queue = event_bus.subscribe(event_type="input")  # subscribe to input events (optionally filter by user if one handler per user; but one global handler can handle all sequentially)
      while True:
          event = await queue.get()
          try:
              await handle_event(event)
          except Exception as e:
              logger.error(f"Error processing event: {e}", exc_info=True)
              # continue loop even if one event fails
  ```
  This simple loop ensures the handler is always running, picking up one event at a time. If an error occurs during processing, catch it so the loop doesn’t break (no event should crash the whole service).
- **Handle Event:** The core logic in `handle_event(event)` for an input message:
  1. **Validate Event Data:** It should contain the message content, user, etc. (All likely provided by the publisher in `/input` route). No heavy lifting here, just extract needed info.
  2. **Retrieve Context (Memory & Cognition):** Option 1 – _Proactive Context:_ Immediately fetch the conversation history from Memory and/or a summary from Cognition. For example, call `history = await memory_client.get_history(user_id, conv_id)` and `context = await cognition_client.get_context(user_id, conv_id)`. Use these to formulate the prompt for the LLM (e.g., “Conversation so far: … [history]. User asks: [latest message]”). This is straightforward but always calls the tools whether needed or not.
     Option 2 – _LLM-Driven Tool Use:_ Use a structured approach where the LLM is first asked if it needs a tool. For instance, send the LLM a prompt with just the user’s query (and maybe some system instruction like “Answer or request a tool”). The LLM might respond either with an answer or a tool request (in a predefined JSON format). Using **pydantic-ai**, attempt to parse the LLM response into the `ToolRequest` model. If it fits, it means the LLM is asking for data (like memory). If not, the LLM response is a final answer.
     - For MVP, a pragmatic approach: you could start with the proactive context (simpler implementation), and once that works, refine with the structured loop if desired. The structured method is more complex but showcases the power of minimal interfaces (LLM output can be parsed and validated easily).
  3. **Call LLM:** Invoke the language model to get a response. Use a direct integration:
     - If an OpenAI API key or similar is available, call the OpenAI API (via their SDK) with an appropriate prompt. Keep the prompt construction simple (e.g., a system message describing the conversation context or instructions, and the user message).
     - If external API use is not possible (due to environment), create a stub function that returns a canned response or echoes the input. This ensures the flow can be tested end-to-end. The integration of the real LLM can be swapped in later.
     - Do not wrap the LLM API in a new abstraction; call it directly in this function. We trust the external library to handle the details.
  4. **Tool Use Loop (if implemented):** If using the pydantic-ai structured output approach:
     - If the first LLM call returns a `ToolRequest` (e.g., asks for “memory”), then perform that tool action (e.g., fetch from Memory service) and then call the LLM again, providing the requested data and prompting for a final answer. This might involve sending a new prompt like “Tool result: … Now please provide the final answer.”
     - Limit this loop to a simple one-hop for MVP (one tool usage at most). We’re not building a full AI agent loop, just demonstrating the pattern.
     - If the first LLM response was already an answer (`FinalAnswer` model), proceed to next step directly.
  5. **Publish Output Event:** Take the final answer (as text or structured data) and publish it on the EventBus as an `"output"` event so that any SSE connections can broadcast it to the client. The event might include the answer text and perhaps a conversation/user identifier. Keep the payload minimal (e.g., `{type: "output", user_id: X, conversation_id: Y, data: {"answer": "text"}}`).
  6. **Optional Enhancements:** You might add small quality-of-life features like splitting a long answer into multiple events for streaming effect, or adding an initial “typing” event. But these are extras – only implement if time permits and it doesn’t add undue complexity. The core requirement is that an output event with the answer eventually gets published for the waiting client.
- **Clarity and Simplicity:** The Response Orchestrator should be written so that its flow is easy to follow by a human. Even though it’s the most involved part of the system, structure it with clear steps (perhaps breaking sub-tasks into helper functions like `get_context()` or `call_llm()` to avoid one huge function). Ensure each sub-step (memory fetch, LLM call, etc.) is understandable in isolation and uses the simplest possible approach to achieve its goal.
- **No Extra Abstraction:** Resist creating a generic “Orchestrator” class with complex state. A simple function (or a module-level coroutine) that uses the already existing components (event bus, clients, LLM SDK) is sufficient. This keeps the data flow transparent.
- **Testing Hooks:** Consider how you would test this in isolation. Perhaps allow injecting a fake LLM function or dummy memory client if needed. Designing with this in mind (like having the LLM call in a helper that can be replaced for tests) will ensure the component’s interface is clear and side-effect free except for the event publishing.

## 9. Application Integration and Startup

**Scope:** Tie all components together in the FastAPI app startup and ensure the system comes up and down cleanly. This step configures the application object, includes routers, and kicks off background tasks and any embedded services. The aim is to achieve a working end-to-end system with minimal bootstrapping code.

- **Main Application Composition:** In `app/main.py`, create the FastAPI app and include all routers from the `api` module (auth, input, output, config). This wires up the HTTP interface. For each router, ensure dependencies like `get_current_user` are applied to protected routes. Keep the inclusion and setup straightforward.
- **Instantiate Global Components:** Ensure that instances of core components are created and accessible:
  - If not already done at import time, instantiate the `event_bus = EventBus()` and perhaps the MCP client connections (or client manager). Attaching them to `app.state` can be a clean way to pass them around (e.g., `app.state.event_bus`). This isn’t strictly necessary if modules have them as singletons, but using `app.state` can clarify lifecycle ownership (tied to the application).
  - Likewise, if the Memory and Cognition services are to be run in-process for convenience, decide on how to start them (see below).
- **Startup Events:** Use `@app.on_event("startup")` to perform initialization tasks asynchronously:
  - **Connect MCP Clients:** Call the connect routine for fastMCP clients to Memory and Cognition. If using lazy connect, this might be a no-op. Otherwise, attempt to connect and log the result. This prepares the core to call services.
  - **Launch Background Services (Optional):** If choosing to auto-start the Memory and Cognition service processes/threads, do it here. For example, you might start a thread for each that runs `memory_service.run()` (ensuring it doesn’t block the main thread). Only do this if it doesn’t add too much complexity; otherwise require the developer to start those services separately for clarity.
  - **Start Response Handler:** Kick off the async task that runs the response handling loop (created in the previous step). This ensures by the time an input comes in, the handler is ready to process events.
  - **Log Ready State:** It’s helpful to log or print that the system started successfully and maybe print the URLs of the key endpoints for quick reference.
- **Shutdown Events:** Use `@app.on_event("shutdown")` to gracefully shut down:
  - Close or disconnect MCP connections if the library requires (to avoid resource leaks).
  - Signal the background response handler to stop if needed (could set a flag that breaks the loop, or cancel the task). Ensure any threads or subprocesses for services are terminated if they were started by the app (this might not be critical for Ctrl-C exit, but good practice).
  - This keeps the teardown clean and avoids dangling processes or open sockets.
- **Minimal Glue, No Surprises:** Avoid any hidden magical wiring. For instance, pass the event_bus or clients explicitly where needed rather than pulling from globals in unpredictable ways. However, do not over-engineer a dependency injection system; the app is small enough to manage by simple imports or using `app.state`. The integration code should feel straightforward, almost script-like, since this is the main assembly of components.
- **Verify Basic Routing:** After startup logic, it’s worth quickly verifying that the app object indeed has all routes mounted (possibly by printing `app.routes` in debug or checking via an HTTP client). This double-check ensures nothing was missed in integration.

## 10. Testing and Validation

**Scope:** Validate the end-to-end functionality and reliability of the MVP through both manual testing and automated tests. This ensures that each component works in isolation and together as a system, and that the design principles (simplicity, clear interfaces, etc.) result in a maintainable, bug-resistant implementation.

- **Manual Testing (End-to-End):** Before writing formal tests, run the system and exercise it like a user would:
  - Start the Memory and Cognition services (if not auto-started) and the Cortex Core FastAPI app.
  - Obtain a JWT for testing: if you implemented `/auth/login`, use it to get a token. If not, you might disable auth in dev or use a pre-generated token signed with the known secret. Make sure the `Authorization` header is correctly used in subsequent calls.
  - Use a tool like curl or HTTPie to POST a sample message to `/input`. For example:
    ```bash
    curl -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d '{"content": "Hello"}' http://localhost:8000/input
    ```
    Expect an acknowledgment response (200 OK).
  - Open a connection to `/output/stream`. This could be done with a specialized SSE client, a simple web frontend, or using `curl`/browser. Verify that after sending the input, an output event is eventually received. You should see the assistant’s reply come through.
  - Try edge cases: invalid token (expect 401), hitting protected endpoints without auth (401), using the config endpoints (create a workspace, then create a conversation, then use that conv ID in input if your logic supports it). Ensure these basic scenarios behave correctly.
  - Observe logs for any errors or warnings to catch unexpected issues. This manual step ensures the core flow is solid before codifying it in tests.
- **Automated Tests:** Write a minimal test suite focusing on critical functionality:
  - **Unit Tests:**
    - EventBus: Simulate subscribing and publishing. For example, subscribe with filter for user A, publish an event for user A and another for user B, and assert that only the correct event is received in the subscriber’s queue. Test multiple subscribers to one user to ensure fan-out works.
    - Auth Utility: If using a static secret for tests, create a JWT (using an external library or a known good token) and verify `get_current_user` returns the expected payload. Also test that a bad token raises the correct exception.
    - Model Schemas: Use Pydantic models in isolation (if any custom validators were added) to ensure they accept valid data and reject invalid (e.g., missing required fields). Pydantic is reliable, so focus on any logic we added.
    - If structured LLM output logic (pydantic-ai models) is used, test the parsing: e.g., given a fake LLM output JSON for a ToolRequest vs a FinalAnswer, ensure the models parse or error as expected.
  - **Integration Tests:**
    - Use FastAPI’s TestClient or AsyncClient to simulate a full request flow. For instance, use an overridden dependency to bypass actual Auth0 (return a test user unconditionally), and an overridden MCP client that doesn’t call real services but returns preset data. This way you can simulate the response handler end-to-end:
      - Example: override the memory client’s `get_history` to return a known list, override LLM call to return a known answer, then in the test call `/input` and read from `/output/stream` (this might involve running the response handler synchronously or polling a test hook).
    - Alternatively, run the app in a test and post an input, then directly call the handle_event function with a crafted event (bypassing SSE) to see that it publishes an output event (you can inspect the EventBus or use a fake subscriber in the test to capture it).
    - Test the config endpoints quickly (they are simple CRUD in memory).
  - Aim for a few representative tests rather than exhaustive coverage, focusing on whether the system’s main pathways work and uphold assumptions. For example, a test that the whole pipeline from input to output works with dummy components validates the integration.
- **Documentation and Readability Checks:** As a form of validation, ensure that each module and function has docstrings or comments reflecting its purpose and any assumptions. This is not a test per se, but it verifies that an engineer (or AI assistant) can understand the code easily, aligning with the project philosophy of clarity. If something was hard to explain in a comment, that might indicate the implementation is more complex than necessary.
- **Iterative Hardening:** If any test or manual step fails, fix the simplest way possible. Use this opportunity to remove any incidental complexity discovered. For example, if setting up the test required complicated dependency injection, perhaps the design can be tweaked for simplicity (like making the EventBus globally accessible eased testing). Continuously refine to eliminate friction.

By completing these mini-projects, we end up with a Cortex Core MVP that is clean, understandable, and minimal. Each component is focused on a single area (auth, API, event handling, service integration, etc.) with clearly defined interfaces and responsibilities. There are no superfluous abstractions – every part exists because it directly contributes to the MVP functionality. This breakdown also ensures that different contributors (human or AI) can implement parts in parallel with well-defined contracts between components. The result should be a vertically sliced, functional system that adheres to the guiding principles and is ready to evolve as needed, without any unnecessary baggage.
