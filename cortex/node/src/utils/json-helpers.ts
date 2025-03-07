/**
 * Helper functions for JSON serialization/deserialization with SQLite storage
 */

/**
 * Safely parses a JSON string to an object
 * @param jsonString The JSON string to parse
 * @param defaultValue Default value to return if parsing fails
 * @returns Parsed object or default value
 */
export function parseJsonString<T>(jsonString: string | null | undefined, defaultValue: T): T {
    if (!jsonString) return defaultValue;

    try {
        return JSON.parse(jsonString) as T;
    } catch (error) {
        console.error('Error parsing JSON string:', error);
        return defaultValue;
    }
}

/**
 * Safely stringifies an object to JSON
 * @param data The data to stringify
 * @param defaultValue Default string to return if stringification fails
 * @returns JSON string or default value
 */
export function stringifyJson<T>(data: T, defaultValue: string = '{}'): string {
    try {
        return JSON.stringify(data);
    } catch (error) {
        console.error('Error stringifying object:', error);
        return defaultValue;
    }
}

/**
 * Parse a JSON string array
 * @param jsonArray The JSON array string to parse
 * @returns String array or empty array if parsing fails
 */
export function parseStringArray(jsonArray: string | null | undefined): string[] {
    return parseJsonString<string[]>(jsonArray, []);
}

/**
 * Helper for working with Session model
 */
export const SessionHelpers = {
    parseConfig: (session: { config: string }) => parseJsonString(session.config, {}),
    parseMetadata: (session: { metadata: string }) => parseJsonString(session.metadata, {})
};

/**
 * Helper for working with ApiKey model
 */
export const ApiKeyHelpers = {
    parseScopes: (apiKey: { scopesJson: string }) => parseStringArray(apiKey.scopesJson)
};

/**
 * Helper for working with Workspace model
 */
export const WorkspaceHelpers = {
    parseConfig: (workspace: { config: string }) => parseJsonString(workspace.config, {}),
    parseMetadata: (workspace: { metadata: string }) => parseJsonString(workspace.metadata, {})
};

/**
 * Helper for working with WorkspaceSharing model
 */
export const WorkspaceSharingHelpers = {
    parsePermissions: (sharing: { permissionsJson: string }) => parseStringArray(sharing.permissionsJson)
};

/**
 * Helper for working with Conversation model
 */
export const ConversationHelpers = {
    parseEntries: (conversation: { entries: string }) => parseJsonString(conversation.entries, []),
    parseMetadata: (conversation: { metadata: string }) => parseJsonString(conversation.metadata, {})
};

/**
 * Helper for working with MemoryItem model
 */
export const MemoryItemHelpers = {
    parseContent: (item: { content: string }) => parseJsonString(item.content, {}),
    parseMetadata: (item: { metadata: string }) => parseJsonString(item.metadata, {})
};

/**
 * Helper for working with Integration model
 */
export const IntegrationHelpers = {
    parseConnectionDetails: (integration: { connectionDetails: string }) =>
        parseJsonString(integration.connectionDetails, {}),
    parseCapabilities: (integration: { capabilitiesJson: string }) =>
        parseStringArray(integration.capabilitiesJson)
};

/**
 * Helper for working with DomainExpertTask model
 */
export const DomainExpertTaskHelpers = {
    parseTaskDetails: (task: { taskDetails: string }) => parseJsonString(task.taskDetails, {}),
    parseResult: (task: { result: string | null }) => parseJsonString(task.result, null),
    parseMetadata: (task: { metadata: string }) => parseJsonString(task.metadata, {})
};
