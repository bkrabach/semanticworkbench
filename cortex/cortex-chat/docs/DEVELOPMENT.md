# Cortex Chat Development Guide

_Date: 2025-03-07_

This guide provides detailed technical information for developers working on the Cortex Chat frontend application.

## Development Environment

### Required Tools

- **Node.js**: v18 or later
- **pnpm**: For package management
- **Git**: For version control
- **VSCode**: Recommended editor (with ESLint, Prettier plugins)

### Environment Setup

1. Set up the Cortex Core backend:
   ```bash
   # In the cortex-core directory
   uv pip install -e ".[dev]"
   uv run uvicorn cortex_core.main:app --reload
   ```

2. Set up the Cortex Chat frontend:
   ```bash
   # In the cortex-chat directory
   pnpm install
   pnpm dev
   ```

The frontend will automatically connect to the backend at `http://127.0.0.1:8000`.

## Key Concepts

### 1. API Integration

The `src/api` directory contains everything related to backend communication:

- `client.ts`: Base API functions and endpoint definitions
- `types.ts`: TypeScript interfaces for API models
- `hooks/`: React Query hooks for data fetching

When adding a new API feature:
1. Add TypeScript interfaces in `types.ts`
2. Add endpoint definitions in `client.ts`
3. Create React Query hooks in the `hooks/` directory

### 2. Component Development

Components follow a feature-based organization:

- `auth/`: Authentication-related components
- `conversation/`: Chat and message components
- `layout/`: Application layout components
- `common/`: Shared utility components
- `workspace/`: Workspace management components

When creating a new component:
1. Place it in the appropriate feature directory
2. Use Fluent UI components for consistent styling
3. Leverage hooks for data and state management
4. Follow the component naming conventions

### 3. Real-time Updates with SSE

The application uses Server-Sent Events (SSE) for real-time updates:

- `useSSE.ts`: Manages SSE connections
- Event handlers update the React Query cache
- UI updates automatically through React Query's cache

When working with real-time features:
1. Use the existing `useSSE` hook to establish connections
2. Add event type definitions to `SseEventType` if needed
3. Implement event handlers that update the React Query cache

### 4. Streaming Message Handling

Handling streaming messages involves:

1. Receiving `message_created` events when a message starts
2. Processing `message_updated` events as content streams in
3. Updating the UI in real-time to show typing indicators
4. Rendering the final message when `is_complete` becomes true

## Common Development Tasks

### Adding a New Component

```tsx
// src/components/example/NewComponent.tsx
import { makeStyles, Text } from '@fluentui/react-components';

const useStyles = makeStyles({
  root: {
    display: 'flex',
    padding: '10px',
  },
});

export interface NewComponentProps {
  title: string;
}

export function NewComponent({ title }: NewComponentProps) {
  const styles = useStyles();
  
  return (
    <div className={styles.root}>
      <Text>{title}</Text>
    </div>
  );
}
```

### Creating a New API Hook

```tsx
// src/api/hooks/useNewFeature.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchData, postData } from '../client';

export function useNewFeature(id: string) {
  return useQuery({
    queryKey: ['new-feature', id],
    queryFn: () => fetchData(`/api/new-feature/${id}`),
  });
}

export function useUpdateNewFeature() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (params: UpdateParams) => 
      postData(`/api/new-feature/${params.id}`, params.data),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['new-feature', variables.id],
      });
    },
  });
}
```

### Styling with Fluent UI

Cortex Chat uses Fluent UI's styling system with makeStyles:

```tsx
import { makeStyles } from '@fluentui/react-components';

const useStyles = makeStyles({
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
    padding: '16px',
    backgroundColor: 'var(--colorNeutralBackground1)',
    borderRadius: '4px',
  },
  header: {
    fontWeight: 'bold',
    fontSize: 'var(--fontSizeBase500)',
  },
  // Use Fluent UI's design tokens for consistency
  content: {
    color: 'var(--colorNeutralForeground1)',
    fontSize: 'var(--fontSizeBase300)',
  },
});

function StyledComponent() {
  const styles = useStyles();
  
  return (
    <div className={styles.container}>
      <div className={styles.header}>Title</div>
      <div className={styles.content}>Content goes here</div>
    </div>
  );
}
```

## Debugging

### React Query Debugging

Enable the React Query DevTools in development by uncommenting the devtools import in `App.tsx`:

```tsx
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';

// In your App component
return (
  <>
    {/* Your app components */}
    <ReactQueryDevtools initialIsOpen={false} />
  </>
);
```

### Network Debugging

Use the browser's Network tab to inspect API calls and SSE connections:
- Filter by "fetch/XHR" to see API requests
- Filter by "EventSource" to see SSE connections

### Authentication Testing

For local development, you can use:
- Development tokens from the Cortex Core documentation
- The `authenticateWithToken` function in the console

## Performance Considerations

- Use React Query's caching to minimize API calls
- Implement virtualization for large message lists
- Optimize re-renders with React.memo where appropriate
- Use code splitting for larger feature modules

## Integration with Cortex Core

As you develop, keep in mind that Cortex Chat is part of the broader Cortex Platform architecture:

1. The chat interface is one of multiple input/output modalities in the platform
2. Backend processing involves the Cortex Core's orchestration capabilities
3. Domain Expert Entities may be involved in generating responses
4. Message content might include tool execution results

## Further Resources

- [Fluent UI Documentation](https://react.fluentui.dev/)
- [React Query Documentation](https://tanstack.com/query/latest/docs/react/overview)
- [TypeScript Documentation](https://www.typescriptlang.org/docs/)
- [React Router Documentation](https://reactrouter.com/en/main)