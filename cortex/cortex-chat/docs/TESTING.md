# Testing Guide

This document outlines the testing strategy, tools, and best practices for the Cortex Chat client.

## Testing Philosophy

The testing approach for Cortex Chat is built around these principles:

1. **Confidence Over Coverage**: Focus on tests that build confidence in the application's behavior
2. **Real-World Scenarios**: Test user journeys and real interaction patterns
3. **Fast Feedback**: Tests should run quickly to support rapid iteration
4. **Maintainability**: Tests should be easy to understand and maintain
5. **Isolation**: Tests should be independent and not affect each other

## Testing Levels

### 1. Unit Tests

Unit tests focus on individual functions and components in isolation.

**Tools**:
- Jest for test running and assertions
- React Testing Library for component testing
- Jest-Fetch-Mock for mocking API calls

**Example Unit Test**:

```javascript
// src/utils/formatters.test.js
import { formatTimestamp, formatMessageContent } from './formatters';

describe('formatTimestamp', () => {
  test('formats UTC timestamp to local time', () => {
    // Mock Date.prototype.toLocaleTimeString
    const originalToLocaleTimeString = Date.prototype.toLocaleTimeString;
    Date.prototype.toLocaleTimeString = jest.fn(() => '3:45 PM');
    
    const result = formatTimestamp('2023-10-15T15:45:00Z');
    expect(result).toBe('3:45 PM');
    
    // Restore original method
    Date.prototype.toLocaleTimeString = originalToLocaleTimeString;
  });
  
  test('returns empty string for invalid timestamp', () => {
    expect(formatTimestamp(null)).toBe('');
    expect(formatTimestamp(undefined)).toBe('');
    expect(formatTimestamp('invalid-date')).toBe('');
  });
});

describe('formatMessageContent', () => {
  test('converts markdown code blocks to HTML', () => {
    const input = 'Try this: ```const x = 1;```';
    const expected = 'Try this: <pre><code>const x = 1;</code></pre>';
    expect(formatMessageContent(input)).toBe(expected);
  });
  
  test('handles non-string inputs by converting to JSON', () => {
    const input = { foo: 'bar' };
    expect(formatMessageContent(input)).toBe(JSON.stringify(input, null, 2));
  });
});
```

**Component Unit Test**:

```javascript
// src/components/MessageItem/MessageItem.test.js
import React from 'react';
import { render, screen } from '@testing-library/react';
import MessageItem from './MessageItem';

describe('MessageItem', () => {
  const mockMessage = {
    id: 'msg-123',
    content: 'Hello world',
    role: 'user',
    created_at_utc: '2023-10-15T15:45:00Z'
  };
  
  test('renders message content correctly', () => {
    render(<MessageItem message={mockMessage} />);
    expect(screen.getByText('Hello world')).toBeInTheDocument();
  });
  
  test('applies correct CSS class based on role', () => {
    const { container } = render(<MessageItem message={mockMessage} />);
    expect(container.firstChild).toHaveClass('user-message');
    
    const assistantMessage = { ...mockMessage, role: 'assistant' };
    const { container: container2 } = render(<MessageItem message={assistantMessage} />);
    expect(container2.firstChild).toHaveClass('assistant-message');
  });
  
  test('formats timestamp correctly', () => {
    // Mock the formatter function
    jest.mock('../../utils/formatters', () => ({
      formatTimestamp: () => '3:45 PM',
      formatMessageContent: content => content
    }));
    
    render(<MessageItem message={mockMessage} />);
    expect(screen.getByText('3:45 PM', { exact: false })).toBeInTheDocument();
  });
});
```

### 2. Integration Tests

Integration tests verify that multiple units work together correctly.

**Tools**:
- Jest for test running
- React Testing Library for rendering and interaction
- MSW (Mock Service Worker) for API mocking

**Example Integration Test**:

```javascript
// src/features/conversation/ConversationView.test.js
import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { rest } from 'msw';
import { setupServer } from 'msw/node';
import ConversationView from './ConversationView';
import { AuthProvider } from '../../contexts/AuthContext';

// Mock the API responses
const server = setupServer(
  rest.get('/api/conversations/conv-123', (req, res, ctx) => {
    return res(ctx.json({
      id: 'conv-123',
      title: 'Test Conversation',
      modality: 'chat',
      created_at_utc: '2023-10-15T14:30:00Z'
    }));
  }),
  
  rest.get('/api/conversations/conv-123/messages', (req, res, ctx) => {
    return res(ctx.json({
      messages: [
        {
          id: 'msg-1',
          conversation_id: 'conv-123',
          content: 'Hello',
          role: 'user',
          created_at_utc: '2023-10-15T14:32:00Z'
        },
        {
          id: 'msg-2',
          conversation_id: 'conv-123',
          content: 'Hi there! How can I help you today?',
          role: 'assistant',
          created_at_utc: '2023-10-15T14:32:05Z'
        }
      ]
    }));
  }),
  
  rest.post('/api/conversations/conv-123/messages', (req, res, ctx) => {
    return res(ctx.json({
      id: 'msg-3',
      conversation_id: 'conv-123',
      content: req.body.content,
      role: 'user',
      created_at_utc: new Date().toISOString()
    }));
  })
);

// Start the server before all tests
beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('ConversationView', () => {
  test('loads and displays conversation with messages', async () => {
    render(
      <AuthProvider>
        <ConversationView conversationId="conv-123" />
      </AuthProvider>
    );
    
    // Initially should show loading state
    expect(screen.getByText('Loading conversation...')).toBeInTheDocument();
    
    // Wait for data to load
    await waitFor(() => {
      expect(screen.getByText('Test Conversation')).toBeInTheDocument();
    });
    
    // Verify messages are displayed
    expect(screen.getByText('Hello')).toBeInTheDocument();
    expect(screen.getByText('Hi there! How can I help you today?')).toBeInTheDocument();
  });
  
  test('allows sending new messages', async () => {
    render(
      <AuthProvider>
        <ConversationView conversationId="conv-123" />
      </AuthProvider>
    );
    
    // Wait for conversation to load
    await waitFor(() => {
      expect(screen.getByText('Test Conversation')).toBeInTheDocument();
    });
    
    // Find input and send button
    const input = screen.getByPlaceholderText('Type your message...');
    const sendButton = screen.getByText('Send');
    
    // Type a message and send it
    fireEvent.change(input, { target: { value: 'New test message' } });
    fireEvent.click(sendButton);
    
    // Message should appear in the list (immediately due to optimistic update)
    expect(screen.getByText('New test message')).toBeInTheDocument();
    
    // Input should be cleared
    expect(input.value).toBe('');
  });
});
```

### 3. End-to-End Tests

E2E tests verify the application works as a whole, simulating real user interactions.

**Tools**:
- Cypress for browser-based testing
- Cypress Testing Library for improved selectors

**Example E2E Test**:

```javascript
// cypress/integration/auth.spec.js
describe('Authentication', () => {
  beforeEach(() => {
    // Clear local storage before each test
    cy.clearLocalStorage();
    cy.visit('/');
  });
  
  it('redirects to login page when not authenticated', () => {
    cy.url().should('include', '/login');
  });
  
  it('allows users to log in', () => {
    // Mock the login API response
    cy.intercept('POST', '/api/auth/login', {
      statusCode: 200,
      body: {
        access_token: 'fake-token-123',
        user: {
          id: 'user-123',
          email: 'test@example.com'
        }
      }
    }).as('loginRequest');
    
    // Fill in the login form
    cy.findByLabelText(/email/i).type('test@example.com');
    cy.findByLabelText(/password/i).type('password123');
    cy.findByRole('button', { name: /login/i }).click();
    
    // Wait for the request to complete
    cy.wait('@loginRequest');
    
    // Should redirect to the dashboard
    cy.url().should('include', '/dashboard');
    
    // User should be greeted
    cy.findByText(/welcome/i).should('be.visible');
    cy.findByText('test@example.com').should('be.visible');
  });
  
  it('shows error message for invalid credentials', () => {
    // Mock the failed login
    cy.intercept('POST', '/api/auth/login', {
      statusCode: 401,
      body: {
        error: {
          code: 'authentication_failed',
          message: 'Invalid credentials provided'
        }
      }
    }).as('failedLogin');
    
    // Fill in the login form with invalid credentials
    cy.findByLabelText(/email/i).type('wrong@example.com');
    cy.findByLabelText(/password/i).type('wrongpassword');
    cy.findByRole('button', { name: /login/i }).click();
    
    // Wait for the request to complete
    cy.wait('@failedLogin');
    
    // Should show error message
    cy.findByText(/invalid credentials/i).should('be.visible');
    cy.url().should('include', '/login');
  });
});
```

**Conversation E2E Test**:

```javascript
// cypress/integration/conversation.spec.js
describe('Conversation Flow', () => {
  beforeEach(() => {
    // Log in and set up initial state
    cy.login('test@example.com', 'password123');
    
    // Mock API responses
    cy.intercept('GET', '/api/workspaces', {
      statusCode: 200,
      body: {
        workspaces: [
          {
            id: 'workspace-123',
            name: 'Test Workspace',
            created_at_utc: '2023-10-14T10:00:00Z'
          }
        ]
      }
    });
    
    cy.intercept('GET', '/api/workspaces/workspace-123/conversations', {
      statusCode: 200,
      body: {
        conversations: [
          {
            id: 'conv-123',
            title: 'Test Conversation',
            modality: 'chat',
            created_at_utc: '2023-10-15T14:30:00Z'
          }
        ]
      }
    });
    
    cy.intercept('GET', '/api/conversations/conv-123/messages', {
      statusCode: 200,
      body: {
        messages: [
          {
            id: 'msg-1',
            conversation_id: 'conv-123',
            content: 'Hello',
            role: 'user',
            created_at_utc: '2023-10-15T14:32:00Z'
          },
          {
            id: 'msg-2',
            conversation_id: 'conv-123',
            content: 'Hi there! How can I help you today?',
            role: 'assistant',
            created_at_utc: '2023-10-15T14:32:05Z'
          }
        ]
      }
    });
    
    cy.visit('/');
  });
  
  it('allows selecting a conversation and viewing messages', () => {
    // Select workspace
    cy.findByRole('combobox', { name: /workspace/i }).select('Test Workspace');
    
    // Click on conversation
    cy.findByText('Test Conversation').click();
    
    // Verify messages are displayed
    cy.findByText('Hello').should('be.visible');
    cy.findByText('Hi there! How can I help you today?').should('be.visible');
  });
  
  it('allows sending a new message and displays response', () => {
    // Mock message sending and SSE updates
    cy.intercept('POST', '/api/conversations/conv-123/messages', {
      statusCode: 200,
      body: {
        id: 'msg-3',
        conversation_id: 'conv-123',
        content: 'What is the weather like?',
        role: 'user',
        created_at_utc: '2023-10-15T15:00:00Z'
      }
    }).as('sendMessage');
    
    // Set up SSE mock
    cy.window().then((win) => {
      const originalEventSource = win.EventSource;
      win.EventSource = function(url) {
        const mockEventSource = {
          addEventListener: jest.fn(),
          close: jest.fn()
        };
        
        // Simulate message event after a delay
        setTimeout(() => {
          const messageEvent = new win.MessageEvent('message_received', {
            data: JSON.stringify({
              id: 'msg-4',
              conversation_id: 'conv-123',
              content: 'The weather is sunny and warm today!',
              role: 'assistant',
              created_at_utc: '2023-10-15T15:00:05Z'
            })
          });
          
          if (mockEventSource.onmessage) {
            mockEventSource.onmessage(messageEvent);
          }
        }, 500);
        
        return mockEventSource;
      };
      
      // Restore original EventSource when test completes
      cy.on('window:before:unload', () => {
        win.EventSource = originalEventSource;
      });
    });
    
    // Select workspace and conversation
    cy.findByRole('combobox', { name: /workspace/i }).select('Test Workspace');
    cy.findByText('Test Conversation').click();
    
    // Type and send a message
    cy.findByPlaceholderText('Type your message...').type('What is the weather like?');
    cy.findByRole('button', { name: /send/i }).click();
    
    // Verify user message appears
    cy.findByText('What is the weather like?').should('be.visible');
    
    // Verify response appears after SSE event
    cy.findByText('The weather is sunny and warm today!').should('be.visible');
  });
  
  it('allows creating a new conversation', () => {
    // Mock conversation creation
    cy.intercept('POST', '/api/workspaces/workspace-123/conversations', {
      statusCode: 200,
      body: {
        id: 'conv-456',
        title: 'New Conversation',
        modality: 'chat',
        created_at_utc: '2023-10-15T15:30:00Z'
      }
    }).as('createConversation');
    
    // Select workspace
    cy.findByRole('combobox', { name: /workspace/i }).select('Test Workspace');
    
    // Click new conversation button
    cy.findByRole('button', { name: /new conversation/i }).click();
    
    // Wait for creation request
    cy.wait('@createConversation');
    
    // New conversation should appear in the list
    cy.findByText('New Conversation').should('be.visible');
    
    // New conversation should be selected
    cy.url().should('include', '/conversations/conv-456');
  });
});
```

## Testing Server-Sent Events (SSE)

Testing SSE connections requires special handling:

1. **Unit Tests**: Mock the EventSource class
2. **Integration Tests**: Use MSW to simulate SSE events
3. **E2E Tests**: Use Cypress-specific techniques to mock EventSource

### SSE Testing Strategy

```javascript
// src/services/sse/sseManager.test.js
import { SSEManager } from './sseManager';

describe('SSEManager', () => {
  let sseManager;
  let mockEventSource;
  
  // Mock the global EventSource
  beforeAll(() => {
    global.EventSource = jest.fn().mockImplementation(() => {
      mockEventSource = {
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        close: jest.fn(),
        // These will be called by the implementation
        onopen: null,
        onerror: null
      };
      return mockEventSource;
    });
  });
  
  beforeEach(() => {
    sseManager = new SSEManager('https://api.example.com');
    sseManager.setTokenProvider(() => 'test-token-123');
    jest.clearAllMocks();
  });
  
  test('connect creates an EventSource with the correct URL', () => {
    sseManager.connect('conversation', '123');
    
    expect(global.EventSource).toHaveBeenCalledWith(
      'https://api.example.com/v1/conversation/123?token=test-token-123'
    );
  });
  
  test('disconnect closes the EventSource', () => {
    sseManager.connect('conversation', '123');
    sseManager.disconnect('conversation_123');
    
    expect(mockEventSource.close).toHaveBeenCalled();
  });
  
  test('triggers event handlers when events are received', () => {
    const mockHandler = jest.fn();
    sseManager.connect('conversation', '123');
    sseManager.on('conversation_123', 'message_received', mockHandler);
    
    // Find the event listener that was registered
    const eventCallback = mockEventSource.addEventListener.mock.calls.find(
      call => call[0] === 'message_received'
    )[1];
    
    // Simulate an event
    eventCallback({
      data: JSON.stringify({ id: 'msg-123', content: 'Test message' })
    });
    
    expect(mockHandler).toHaveBeenCalledWith({ 
      id: 'msg-123', 
      content: 'Test message' 
    });
  });
  
  test('handles connection errors', () => {
    const mockHandler = jest.fn();
    sseManager.connect('conversation', '123');
    sseManager.on('conversation_123', 'error', mockHandler);
    
    // Simulate error event
    mockEventSource.onerror(new Error('Connection failed'));
    
    expect(mockHandler).toHaveBeenCalled();
  });
});
```

## Mocking Strategies

### API Mocking

```javascript
// __mocks__/apiClient.js
const apiClient = {
  get: jest.fn().mockImplementation((url) => {
    if (url.includes('/workspaces')) {
      return Promise.resolve({
        data: {
          workspaces: [
            { id: 'ws-1', name: 'Workspace 1' },
            { id: 'ws-2', name: 'Workspace 2' }
          ]
        }
      });
    }
    
    if (url.includes('/conversations')) {
      return Promise.resolve({
        data: {
          conversations: [
            { id: 'conv-1', title: 'Conversation 1' },
            { id: 'conv-2', title: 'Conversation 2' }
          ]
        }
      });
    }
    
    // Default fallback
    return Promise.resolve({ data: {} });
  }),
  
  post: jest.fn().mockImplementation((url, data) => {
    if (url.includes('/auth/login')) {
      return Promise.resolve({
        data: {
          access_token: 'test-token-123',
          user: { id: 'user-1', email: 'test@example.com' }
        }
      });
    }
    
    if (url.includes('/messages')) {
      return Promise.resolve({
        data: {
          id: 'msg-new',
          content: data.content,
          role: data.role,
          created_at_utc: new Date().toISOString()
        }
      });
    }
    
    return Promise.resolve({ data: {} });
  })
};

export default apiClient;
```

### Context Mocking

```javascript
// src/testUtils.js
import React from 'react';
import { render as rtlRender } from '@testing-library/react';
import { AuthContext } from './contexts/AuthContext';

// Custom render function that wraps components with necessary providers
function render(
  ui,
  {
    authState = { 
      user: { id: 'user-1', email: 'test@example.com' },
      isAuthenticated: true
    },
    ...renderOptions
  } = {}
) {
  function Wrapper({ children }) {
    return (
      <AuthContext.Provider 
        value={{ 
          ...authState,
          login: jest.fn(),
          logout: jest.fn()
        }}
      >
        {children}
      </AuthContext.Provider>
    );
  }
  return rtlRender(ui, { wrapper: Wrapper, ...renderOptions });
}

// Re-export everything from React Testing Library
export * from '@testing-library/react';

// Override the render method
export { render };
```

## Test Organization

Organize tests to mirror the source code structure:

```
src/
├── components/
│   ├── Button/
│   │   ├── Button.js
│   │   ├── Button.test.js
│   │   └── index.js
│   └── MessageList/
│       ├── MessageList.js
│       ├── MessageList.test.js
│       └── index.js
├── services/
│   ├── api/
│   │   ├── api.js
│   │   ├── api.test.js
│   │   └── index.js
│   └── sse/
│       ├── sseManager.js
│       ├── sseManager.test.js
│       └── index.js
└── utils/
    ├── formatters.js
    └── formatters.test.js

cypress/
├── fixtures/
│   ├── users.json
│   └── messages.json
├── integration/
│   ├── auth.spec.js
│   ├── conversation.spec.js
│   └── workspace.spec.js
└── support/
    ├── commands.js
    └── index.js
```

## Testing Best Practices

### General

1. **Test Behavior, Not Implementation**: Focus on what the code does, not how it's written
2. **Use Descriptive Test Names**: Make test names clear about what they're testing
3. **Arrange-Act-Assert Pattern**: Structure tests with clear setup, action, and verification
4. **Avoid Test Interdependence**: Each test should be able to run independently
5. **Clean Up After Tests**: Remove any global state modifications

### React Components

1. **Test User Interactions**: Test what users do, not implementation details
2. **Avoid Testing Props Directly**: Test the rendered output, not the props themselves
3. **Test Accessibility**: Verify key accessibility features
4. **Use Screen Queries**: Prefer screen queries over container queries
5. **User-Centric Selectors**: Use selectors that users would use to find elements

### API and Async

1. **Mock External Dependencies**: Isolate tests from external services
2. **Test Happy and Error Paths**: Verify both successful and failed requests
3. **Avoid Timeout Races**: Use proper async/await and waitFor patterns
4. **Test Loading States**: Verify loading indicators are shown appropriately
5. **Verify Request Parameters**: Check that API calls include correct data

### SSE Testing

1. **Mock EventSource**: Replace the global EventSource with a controlled mock
2. **Test Reconnection Logic**: Verify reconnection behavior on connection failures
3. **Trigger Fake Events**: Simulate events to test handling logic
4. **Verify Clean Shutdown**: Ensure connections are properly closed

## Common Testing Patterns

### Testing Asynchronous Behavior

```javascript
test('loads data asynchronously', async () => {
  // Render with a loading state
  const { rerender } = render(<DataLoader />);
  
  // Verify loading state is shown
  expect(screen.getByText('Loading...')).toBeInTheDocument();
  
  // Wait for loading to complete
  await waitFor(() => {
    expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
  });
  
  // Verify data is displayed
  expect(screen.getByText('Data item 1')).toBeInTheDocument();
});
```

### Testing Error Handling

```javascript
test('shows error message when API fails', async () => {
  // Mock API to return an error
  apiClient.get.mockImplementationOnce(() => 
    Promise.reject(new Error('API Error'))
  );
  
  render(<DataLoader />);
  
  // Wait for error message to appear
  await waitFor(() => {
    expect(screen.getByText('Failed to load data')).toBeInTheDocument();
  });
  
  // Verify retry button is present
  const retryButton = screen.getByRole('button', { name: /retry/i });
  expect(retryButton).toBeInTheDocument();
  
  // Test retry functionality
  apiClient.get.mockImplementationOnce(() => 
    Promise.resolve({ data: { items: ['Data item 1'] } })
  );
  
  fireEvent.click(retryButton);
  
  // Verify loading state returns
  expect(screen.getByText('Loading...')).toBeInTheDocument();
  
  // Wait for success state
  await waitFor(() => {
    expect(screen.getByText('Data item 1')).toBeInTheDocument();
  });
});
```

### Testing Form Submission

```javascript
test('handles form submission correctly', async () => {
  const mockSubmit = jest.fn();
  
  render(<LoginForm onSubmit={mockSubmit} />);
  
  // Fill in form fields
  fireEvent.change(screen.getByLabelText(/email/i), {
    target: { value: 'user@example.com' }
  });
  
  fireEvent.change(screen.getByLabelText(/password/i), {
    target: { value: 'password123' }
  });
  
  // Submit the form
  fireEvent.click(screen.getByRole('button', { name: /login/i }));
  
  // Verify submission handler was called with correct data
  expect(mockSubmit).toHaveBeenCalledWith({
    email: 'user@example.com',
    password: 'password123'
  });
});
```

## Continuous Integration

Configure CI to run tests automatically on push and pull requests:

```yaml
# .github/workflows/test.yml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Setup Node.js
      uses: actions/setup-node@v2
      with:
        node-version: '16'
        cache: 'npm'
    
    - name: Install dependencies
      run: npm ci
    
    - name: Run linting
      run: npm run lint
    
    - name: Run unit and integration tests
      run: npm test -- --coverage
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v2
    
    - name: Run e2e tests
      run: npm run cy:run
```

## Conclusion

Following these testing practices will help ensure the Cortex Chat client is robust, reliable, and maintainable. Adapt these guidelines to specific project needs and evolve them as the application grows.

Remember that the goal of testing is not just to catch bugs, but to enable confident changes, support refactoring, and document expected behavior.