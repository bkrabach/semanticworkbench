/**
 * Memory System Interface for Cortex Core
 * Defines the contract for memory systems (Whiteboard, JAKE, etc.)
 */

export interface MemoryConfig {
  storageType: "in_memory" | "persistent";
  retentionPolicy?: RetentionPolicy;
  encryptionEnabled: boolean;
}

export interface MemoryItem {
  id?: string;
  type: "message" | "entity" | "file" | "event";
  content: any;
  metadata: Record<string, any>;
  timestamp: Date;
  expiresAt?: Date;
}

export interface MemoryQuery {
  types?: string[];
  fromTimestamp?: Date;
  toTimestamp?: Date;
  contentQuery?: string;
  metadataFilters?: Record<string, any>;
  limit?: number;
  includeExpired?: boolean;
}

export interface SynthesizedMemory {
  rawItems: MemoryItem[];
  summary: string;
  entities: Record<string, any>;
  relevanceScore: number;
}

export interface RetentionPolicy {
  defaultTtlDays: number;
  typeSpecificTtl?: Record<string, number>; // type -> days
  maxItems?: number;
}

/**
 * Interface for memory systems in Cortex Core
 * This provides a consistent contract that all memory implementations
 * (Whiteboard, JAKE, etc.) must adhere to
 */
export interface MemorySystemInterface {
  /**
   * Initialize the memory system
   * @param config Configuration options
   */
  initialize(config: MemoryConfig): Promise<void>;
  
  /**
   * Store a memory item
   * @param workspaceId The ID of the workspace
   * @param item The memory item to store
   * @returns The ID of the stored item
   */
  store(workspaceId: string, item: MemoryItem): Promise<string>;
  
  /**
   * Retrieve memory items based on a query
   * @param workspaceId The ID of the workspace
   * @param query The query parameters
   * @returns Array of memory items
   */
  retrieve(workspaceId: string, query: MemoryQuery): Promise<MemoryItem[]>;
  
  /**
   * Update an existing memory item
   * @param workspaceId The ID of the workspace
   * @param itemId The ID of the item to update
   * @param updates The updates to apply
   */
  update(workspaceId: string, itemId: string, updates: Partial<MemoryItem>): Promise<void>;
  
  /**
   * Delete a memory item
   * @param workspaceId The ID of the workspace
   * @param itemId The ID of the item to delete
   */
  delete(workspaceId: string, itemId: string): Promise<void>;
  
  /**
   * Generate a synthetic/enriched context from raw memory
   * @param workspaceId The ID of the workspace
   * @param query The query parameters
   * @returns Synthesized memory
   */
  synthesizeContext(workspaceId: string, query: MemoryQuery): Promise<SynthesizedMemory>;
}

export default MemorySystemInterface;
