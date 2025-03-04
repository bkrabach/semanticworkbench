# Cortex Core Architecture and MCP Connectivity Design

_Version: Draft 0.1_

_Date: 2025-03-04_

---

## 1. Overview

The Cortex platform is designed around a centralized AI Core that orchestrates memory, reasoning, and adaptive task management. This core not only drives the system's primary intelligence but also serves as the connective hub through which all other components communicate via the Model Context Protocol (MCP).

The core is built to be **modular** (composable and interchangeable), providing default implementations for key subsystems. At the same time, it allows these components to be replaced or extended by third-party or community-driven alternatives. This document details the architecture of the Cortex Core and its connectivity via MCP.

---

## 2. Design Principles

- **Unified Intelligence:** The Cortex Core integrates a memory subsystem (inspired by JAKE) and a cognition subsystem to synthesize high-level "memories" and derive actionable insights.

- **Modular, Interchangeable Components:** Each component—whether it is the memory system, cognition engine, or I/O handler—comes with a default implementation but is designed to be hot-swappable. This flexibility extends to domain expert systems (like Code Assistant and Deep Research), which are connected via MCP.

- **MCP-Centric Connectivity:** MCP is the main connectivity backbone for all communications between the Cortex Core and external elements. The client aspect of MCP is embedded directly within the core, ensuring seamless messaging across:

  - Domain Expert Systems
  - External integration tools (e.g., VS Code Extension, M365 Apps, Browser Extensions)
  - Any other service in the ecosystem

- **Adaptive Interaction:** The core intelligently adapts to the available I/O modalities. For instance, it supports dual voice processing approaches (traditional speech-to-text with text-to-speech, as well as real-time voice streaming via the OpenAI realtime API) to reduce latency and enhance the user experience.

---

## 3. Architectural Components

### 3.1. Central AI Core

- **Responsibilities:**

  - **Task Orchestration & Routing:** Routes inputs, updates memory context, triggers cognition, and selects the best output modality based on context.
  - **API Exposure:** Provides REST endpoints, an OpenAI-compatible API, and MCP connectivity to interact with both front-end interfaces and external services.
  - **MCP Integration:** Embeds the MCP client functionality, enabling standardized communication with domain expert systems and community MCP servers.

- **Implementation:**
  - Built on FastAPI (Python) to ensure lightweight, scalable interactions.

### 3.2. Memory and Cognition Systems

- **Memory System:**

  - Synthesizes high-level memories from interactions without storing raw conversation history.
  - Uses vector-based semantic search to retrieve context relevant for decision-making.

- **Cognition System:**
  - Processes memory updates to generate insights and orchestrate responses.
  - Decides when to delegate tasks to domain expert systems or external integrations via MCP.

### 3.3. I/O Modalities

- **Inputs:**

  - **Chat Input:** Textual communication, including markdown and multi-language support.
  - **Voice Input (Two Flavors):**
    - Traditional: Speech-to-text conversion.
    - Real-Time: Audio streaming via OpenAI realtime API for low-latency interaction.
  - **Canvas Input:** Visual or graphical inputs for direct user sketches or images.

- **Outputs:**
  - **Chat Output:** Formatted text responses.
  - **Voice Output (Two Flavors):**
    - Traditional: Text-to-speech synthesis.
    - Real-Time: Streaming audio responses for real-time conversations.
  - **Canvas, Dashboard & Notification Outputs:** Visual displays, detailed visualizations, and alerts respectively.

### 3.4. Domain Expert Systems

- Represent specialized intelligence modules (e.g., Code Assistant and Deep Research) that are connected to the core via MCP.
- These systems are examples; they can be replaced by third-party or community alternatives without affecting the overall architecture.

---

## 4. MCP Connectivity

- MCP serves as the primary communication channel between the core and all external or domain expert systems.
- **Integration:**
  - The Cortex Core's MCP client functionality is embedded directly within the core, allowing seamless tool/resource discovery, standardized message framing, and robust client-server interactions.
  - This design encourages a vibrant ecosystem of community MCP servers and third-party integrations, promoting interoperability while retaining the core's intelligence.

---

## 5. Future Enhancements

- **Workspaces:** A near-term addition to organize projects, artifacts, and contextual information, integrated with the core for efficient context management.
- **Enhanced Domain Expert Flexibility:** Further refinement of the interfaces and protocols to enable more dynamic hot-swapping of expert systems.

---

## 6. Summary

This document outlines the strategic design for the Cortex Core, emphasizing modularity, adaptive interaction, and robust MCP-centric connectivity. It provides a high-level blueprint that drives both current implementations and future extensions, ensuring that the core remains flexible, scalable, and ready to integrate with a thriving ecosystem of domain experts and external tools.
