# Cortex Core Data Models

## Overview

This document outlines the core data models used in the Cortex Core system. These models define the structure of data for users, workspaces, conversations, messages, and files. All models inherit from a common base that includes a flexible `metadata` field (of type `dict[str, Any]`), which provides the ability to attach experimental, debug, or auxiliary data without modifying the core schema.

## Base Model

All core models extend from this base model to ensure consistency and flexibility.

```python
from pydantic import BaseModel, Field
from typing import Any, Dict

class BaseModelWithMetadata(BaseModel):
    """
    A base model that includes a metadata field for storing extra information such as
    experimental flags or debug data.
    """
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

## User Model

The `User` model represents a system user. In this design, every user is uniquely identified (using a value derived from Azure AD B2C) and includes important fields such as name and email which are required.

```python
class User(BaseModelWithMetadata):
    """
    Represents a system user.
    All fields are required.
    """
    user_id: str
    name: str
    email: str
```

## Workspace Model

A `Workspace` is a top-level container that groups together conversations, files, and other artifacts related to a particular topic. The model includes a description, which is required, and an owner identifier linked to the user.

```python
class Workspace(BaseModelWithMetadata):
    """
    Represents a workspace for grouping related conversations and files.
    The description is required.
    """
    id: str
    name: str
    description: str
    owner_id: str  # This field corresponds to the unique B2C user id.
```

## Conversation Model

A `Conversation` belongs to a workspace and consists of a series of messages exchanged around a certain topic. The topic field is mandatory to give context to the conversation.

```python
from typing import List

class Conversation(BaseModelWithMetadata):
    """
    Represents a conversation within a workspace.
    The topic of the conversation is required.
    """
    id: str
    workspace_id: str
    topic: str
    participant_ids: List[str]  # List of user ids participating in the conversation.
```

## Message Model

The `Message` model represents an individual message within a conversation. It captures the sender, content, and timestamp of when the message was sent.

```python
class Message(BaseModelWithMetadata):
    """
    Represents a single message in a conversation.
    """
    id: str
    conversation_id: str
    sender_id: str
    content: str
    timestamp: str  # In practice, consider using a datetime field.
```

## File Model

The optional `File` model is used for handling attachments. It stores file details such as URL, name, and the user who uploaded the file.

```python
class File(BaseModelWithMetadata):
    """
    Represents an attached file within a conversation.
    """
    id: str
    conversation_id: str
    file_name: str
    file_url: str  # URL to where the file is stored.
    uploaded_by: str
    timestamp: str
```

## Summary and Usage

- **Flexibility:**
  The inclusion of the `metadata` field on all models provides flexibility to attach various pieces of auxiliary data without changing the core model structure.

- **Consistency:**
  These models serve as the canonical data structures for both the API contracts (used in FastAPI endpoints) and for persistent storage (via the database, which is SQLite for development and PostgreSQL for production).

- **Extensibility:**
  As the system evolves, additional fields can be added directly to the primary model definitions. Meanwhile, the `metadata` field ensures that experimental or temporary data can also be recorded without disrupting the overall schema.

This document and the accompanying code examples serve as a foundation for the Cortex Core data layer. Further adjustments and extensions can be made as new requirements emerge.
