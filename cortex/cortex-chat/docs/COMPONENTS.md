# Component Reference

This document provides a reference for the components in the Cortex Chat client, their purpose, and usage guidelines.

## Current Components

### Auth Components

These components relate to authentication and user management:

#### `<AuthProvider>`

Provides authentication context to the application.

**Usage**:
```tsx
<AuthProvider>
  <App />
</AuthProvider>
```

**Props**:
- `children`: React nodes to be wrapped by the provider

#### `<ProtectedRoute>`

Ensures routes are only accessible to authenticated users.

**Usage**:
```tsx
<Route 
  path="/dashboard" 
  element={
    <ProtectedRoute>
      <Dashboard />
    </ProtectedRoute>
  } 
/>
```

**Props**:
- `children`: React nodes to render when authenticated

### Layout Components

These components handle the layout and structure of the application:

#### `<AppLayout>`

Provides the main layout structure for the application, including a responsive header, collapsible sidebar, and footer.

**Usage**:
```tsx
<AppLayout
  user={currentUser}
  onLogout={handleLogout}
  sidebar={sidebarContent}
>
  <YourContent />
</AppLayout>
```

**Props**:
- `children`: Content to display in the main area
- `sidebar`: React node to display in the sidebar
- `user`: User object with information for the header
- `onLogout`: Function to handle user logout
- `className`: Optional CSS class name

Features:
- Full viewport coverage with proper sizing on all devices
- Properly handles mobile and desktop screens with responsive breakpoints
- Automatically adjusts to available screen space
- Collapsible sidebar with toggle button
- User menu in the header with logout option
- Persistent footer
- Properly handles overflow in content areas
- Uses CSS variables for consistent styling
- Implements Fluent UI design system tokens for consistency
- Mobile-optimized interactions and touch targets
- Maintains proper accessibility for keyboard navigation
- Prevents content from being obscured on small screens

### Chat Components

Components for chat functionality:

#### `<MessageList>`

Displays a list of messages in a conversation with proper styling for different message types.

**Usage**:
```tsx
<MessageList 
  messages={messages} 
  isLoading={isLoading}
  isTyping={isTyping}
  conversationTitle="Conversation Title"
/>
```

**Props**:
- `messages`: Array of message objects
- `isLoading`: Boolean indicating if messages are loading
- `isTyping`: Boolean indicating if the assistant is typing
- `conversationTitle`: Optional title to display in empty state
- `className`: Optional CSS class name

#### `<MessageItem>`

Renders a single message with appropriate styling based on the sender (user, assistant, system).

**Usage**:
```tsx
<MessageItem 
  message={message}
/>
```

**Props**:
- `message`: Message object to render

#### `<MessageInput>`

Provides a textarea for composing and sending messages with auto-resize functionality.

**Usage**:
```tsx
<MessageInput 
  onSendMessage={handleSendMessage} 
  isDisabled={!isConnected}
  placeholder="Type your message..."
  maxLength={2000} 
/>
```

**Props**:
- `onSendMessage`: Function called when a message is sent
- `isDisabled`: Boolean to disable input when disconnected
- `placeholder`: Text placeholder
- `maxLength`: Maximum character limit
- `className`: Optional CSS class name

#### `<ConversationView>`

Provides a complete view of a conversation, including message list, input, and conversation details.

**Usage**:
```tsx
<ConversationView 
  conversation={conversation}
  isLoading={isLoading}
  isTyping={isTyping}
  onSendMessage={handleSendMessage}
  onEditTitle={handleEditTitle}
  onDeleteConversation={handleDeleteConversation}
/>
```

**Props**:
- `conversation`: Conversation object with messages
- `isLoading`: Boolean indicating loading state
- `isTyping`: Boolean indicating typing state
- `onSendMessage`: Function to handle sending messages
- `onEditTitle`: Optional function to edit conversation title
- `onDeleteConversation`: Optional function to delete conversation
- `className`: Optional CSS class name

### Workspace Components

Components for managing workspaces:

#### `<WorkspaceList>`

Displays a list of available workspaces with selection and creation functionality.

**Usage**:
```tsx
<WorkspaceList 
  workspaces={workspaces}
  selectedWorkspaceId={selectedId}
  onSelectWorkspace={handleSelectWorkspace}
  onCreateWorkspace={handleCreateWorkspace}
  onDeleteWorkspace={handleDeleteWorkspace}
/>
```

**Props**:
- `workspaces`: Array of workspace objects
- `selectedWorkspaceId`: ID of the currently selected workspace
- `onSelectWorkspace`: Function called when a workspace is selected
- `onCreateWorkspace`: Function called to create a new workspace
- `onDeleteWorkspace`: Optional function to delete workspaces

#### `<ConversationList>`

Displays a list of conversations in the current workspace with selection and management options.

**Usage**:
```tsx
<ConversationList 
  conversations={conversations}
  currentConversationId={currentId}
  onSelectConversation={handleSelectConversation}
  onCreateConversation={handleCreateConversation}
  onDeleteConversation={handleDeleteConversation}
  onRenameConversation={handleRenameConversation}
  isLoading={isLoading}
/>
```

**Props**:
- `conversations`: Array of conversation objects
- `currentConversationId`: ID of the currently selected conversation
- `onSelectConversation`: Function called when a conversation is selected
- `onCreateConversation`: Function called to create a new conversation
- `onDeleteConversation`: Optional function to delete conversations
- `onRenameConversation`: Optional function to rename conversations
- `isLoading`: Boolean indicating loading state

## Component Design Guidelines

When creating new components for Cortex Chat, follow these guidelines:

### Component Structure

1. **Single Responsibility**: Each component should do one thing well
2. **Proper Typing**: Use TypeScript interfaces for props
3. **Default Props**: Provide sensible defaults when applicable
4. **Error States**: Handle error states gracefully
5. **Loading States**: Show loading indicators when data is loading

### Example Component Template

```tsx
import React from 'react';
import { useTheme } from '@fluentui/react-components';

interface MyComponentProps {
    title: string;
    isLoading?: boolean;
    onAction?: () => void;
}

export const MyComponent: React.FC<MyComponentProps> = ({
    title,
    isLoading = false,
    onAction
}) => {
    const theme = useTheme();
    
    if (isLoading) {
        return <div>Loading...</div>;
    }
    
    return (
        <div>
            <h2>{title}</h2>
            {onAction && (
                <button onClick={onAction}>
                    Perform Action
                </button>
            )}
        </div>
    );
};
```

### Accessibility Guidelines

1. Use semantic HTML (headings, lists, etc.)
2. Ensure keyboard navigation works
3. Use ARIA attributes when necessary
4. Maintain sufficient color contrast
5. Support screen readers with appropriate text alternatives

## Implementation Roadmap

The implementation roadmap for components is as follows:

1. **Phase 1: Core Structure**
   - Basic layout components
   - Authentication components
   - Navigation components

2. **Phase 2: Chat Functionality**
   - Message display components
   - Message input components
   - Real-time update indicators

3. **Phase 3: Workspace Management**
   - Workspace selection and creation
   - Conversation management
   - Resource viewing

4. **Phase 4: Advanced Features**
   - Multi-modal inputs (voice, canvas)
   - Rich content rendering
   - Notifications and alerts