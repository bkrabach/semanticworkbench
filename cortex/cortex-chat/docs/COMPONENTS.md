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

### Layout Components (Planned)

These components handle the layout and structure of the application:

#### `<AppLayout>` (Future)

Will provide the main layout structure for the application, including navigation, sidebars, and content areas.

**Usage**:
```tsx
<AppLayout>
  <YourContent />
</AppLayout>
```

#### `<Sidebar>` (Future)

Will provide a sidebar for navigation, workspace selection, etc.

**Usage**:
```tsx
<Sidebar>
  <WorkspaceList />
  <ConversationList />
</Sidebar>
```

### Chat Components (Planned)

Components for chat functionality:

#### `<MessageList>` (Future)

Will display a list of messages in a conversation.

**Usage**:
```tsx
<MessageList 
  messages={messages} 
  isLoading={isLoading} 
/>
```

#### `<MessageInput>` (Future)

Will provide an input field for sending messages.

**Usage**:
```tsx
<MessageInput 
  onSendMessage={handleSendMessage} 
  isDisabled={!isConnected} 
/>
```

#### `<ConversationView>` (Future)

Will provide a complete view of a conversation, including messages and input.

**Usage**:
```tsx
<ConversationView 
  conversationId={id} 
/>
```

### Workspace Components (Planned)

Components for managing workspaces:

#### `<WorkspaceList>` (Future)

Will display a list of available workspaces.

**Usage**:
```tsx
<WorkspaceList 
  workspaces={workspaces} 
  onSelectWorkspace={handleSelectWorkspace} 
/>
```

#### `<ConversationList>` (Future)

Will display a list of conversations in the current workspace.

**Usage**:
```tsx
<ConversationList 
  conversations={conversations} 
  currentConversationId={currentId} 
  onSelectConversation={handleSelectConversation} 
/>
```

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