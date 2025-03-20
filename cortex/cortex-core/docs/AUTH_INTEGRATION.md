# Cortex Core Authentication and Azure AD B2C Integration

## Overview

The Cortex Core abstracts all authentication details so that clients (both input and output) always interact with the same set of endpoints regardless of whether the system is running locally or on a production Azure environment. In production, Cortex Core will integrate with Azure AD B2C using standard OpenID Connect (OIDC) protocols; for the MVP and development, stub endpoints provide the necessary authentication behavior.

All authentication endpoints are designed to:

- Issue and validate JSON Web Tokens (JWT) that include standard Azure AD B2C claim names.
- Allow clients to login and verify tokens without needing to manage external URLs.
- Partition data by extracting a unique user identifier (the `oid` claim) from the token.

## Authentication Endpoints

### 1. Login Endpoint

**Purpose:**
In a production scenario, the authentication flow uses Azure AD B2C’s endpoints so that users are redirected to the B2C login page and then return with an ID token and access token. For our MVP, a stubbed `/auth/login` endpoint mimics a successful login flow by validating user credentials against a test store, and then issues a JWT containing essential B2C-style claims.

**Endpoint Details:**

- **URL:** `/auth/login`
- **Method:** POST
- **Request Body:**

  ```json
  {
    "email": "user@example.com",
    "password": "testpassword"
  }
  ```

- **Response:**

  ```json
  {
    "access_token": "dummy-jwt-token-with-claims",
    "token_type": "bearer",
    "expires_in": 3600,
    "claims": {
      "oid": "unique-user-id",
      "email": "user@example.com",
      "name": "User Name"
    }
  }
  ```

**Notes:**

- In production, the Cortex Core will not directly handle user credentials; instead, users will be redirected to Azure AD B2C. The core will then validate the token in incoming requests by using B2C public keys and metadata.
- The stub implementation here is used solely for testing and development, ensuring that all clients use the same authentication interface, regardless of the environment.

### 2. Token Verification Endpoint

**Purpose:**
This endpoint verifies the access token provided in the HTTP Authorization header. Under production conditions, token validation will use Azure AD B2C’s metadata. For the MVP, this stub endpoint decodes the token and returns the embedded claims.

**Endpoint Details:**

- **URL:** `/auth/verify`
- **Method:** GET
- **Request:**
  The client sends the JWT as a bearer token in the Authorization header.

  Example Header:

  ```
  Authorization: Bearer dummy-jwt-token-with-claims
  ```

- **Response:**

  ```json
  {
    "user_id": "unique-user-id",
    "email": "user@example.com",
    "name": "User Name"
  }
  ```

## Authentication Abstraction

The Cortex Core ensures that clients always interact with its authentication endpoints (e.g. `/auth/login` and `/auth/verify`) irrespective of the deployment environment.

- **Core Behavior:**

  - For local development, the stub endpoints provide dummy JWT tokens and simple validation.
  - In production, the Cortex Core will be configured with Azure AD B2C details (such as tenant, client ID/secret, and endpoint URLs). The core will redirect authentication requests to B2C and validate incoming tokens using an OIDC library.
  - Clients do not need to change their authentication URLs between development and production. They simply call the core's endpoints, and the core handles authentication transparently.

- **User Partitioning:**
  The unique user identifier is extracted (from the `oid` claim) on every authenticated request. This user id is used throughout Cortex Core for data partitioning (e.g. storing inputs, managing workspaces) and ensures multi-user support is consistent and secure.

## Implementation Considerations

- **Security:**
  Consider using established OIDC libraries to handle production token validation. This includes periodic key fetching from B2C and proper error handling for expired or malformed tokens.

- **Extensibility:**
  The authentication abstraction layer is designed so that if future requirements necessitate additional claims or integration with other identity providers, the changes remain encapsulated within the core and do not affect the clients.

- **Consistency:**
  All other API endpoints (input, configuration, output streaming) are secured using tokens validated by these auth endpoints. This ensures that the Cortex Core consistently manages multi-user data partitioning and access control.

## Summary

This document outlines how Cortex Core manages authentication by abstracting Azure AD B2C details behind its own `/auth/login` and `/auth/verify` endpoints. The design ensures that clients have a unified interface for authentication, allowing for smooth transitions between local development and production deployments without requiring client-side modifications.

_This flexible and secure approach to authentication helps maintain the integrity of multi-user data while simplifying client integration._
