// ─── Zenic-Agents v3 — Playbook Engine Core Operations ──────────────────
// Standalone CRUD helper functions that wrap PlaybookEngine methods.
// Provides a functional API alongside the class-based PlaybookEngine.

import type {
  PlaybookDocument,
  Industry,
  CertificationStatus,
  PlaybookSearchCriteria,
  PlaybookEngineConfig,
} from "../types";
import { PlaybookEngine, getPlaybookEngine } from "./types";
import type { PlaybookDbRecord } from "./types";

// ─── Functional CRUD Wrappers ─────────────────────────────────────────

/**
 * Create a new playbook from a compiled PlaybookDocument.
 * Uses the singleton PlaybookEngine instance.
 */
export async function createPlaybook(
  doc: PlaybookDocument,
  sourceYaml?: string,
): Promise<PlaybookDbRecord> {
  const engine = getPlaybookEngine();
  return engine.createPlaybook(doc, sourceYaml);
}

/**
 * Get a single playbook by its playbook ID.
 * Uses the singleton PlaybookEngine instance.
 */
export async function getPlaybook(playbookId: string): Promise<PlaybookDbRecord | null> {
  const engine = getPlaybookEngine();
  return engine.getPlaybook(playbookId);
}

/**
 * List playbooks with optional filters.
 * Uses the singleton PlaybookEngine instance.
 */
export async function listPlaybooks(filters?: {
  industry?: Industry;
  isActive?: boolean;
  certificationStatus?: CertificationStatus;
}): Promise<PlaybookDbRecord[]> {
  const engine = getPlaybookEngine();
  return engine.listPlaybooks(filters);
}

/**
 * Update an existing playbook with a new PlaybookDocument.
 * Uses the singleton PlaybookEngine instance.
 */
export async function updatePlaybook(
  playbookId: string,
  doc: PlaybookDocument,
): Promise<PlaybookDbRecord> {
  const engine = getPlaybookEngine();
  return engine.updatePlaybook(playbookId, doc);
}

/**
 * Deactivate a playbook (soft delete — sets isActive to false).
 * Uses the singleton PlaybookEngine instance.
 */
export async function deactivatePlaybook(playbookId: string): Promise<PlaybookDbRecord> {
  const engine = getPlaybookEngine();
  return engine.deactivatePlaybook(playbookId);
}

/**
 * Search playbooks by structured criteria.
 * Uses the singleton PlaybookEngine instance.
 */
export async function searchPlaybooks(criteria: PlaybookSearchCriteria): Promise<{
  playbooks: PlaybookDocument[];
  total: number;
  offset: number;
  limit: number;
}> {
  const engine = getPlaybookEngine();
  return engine.searchPlaybooks(criteria);
}

// ─── Cache Management Utilities ──────────────────────────────────────

/**
 * Clear the playbook engine cache.
 * Useful after bulk operations or when data may be stale.
 */
export function clearEngineCache(): void {
  const engine = getPlaybookEngine();
  engine.clearCache();
}

/**
 * Create a scoped PlaybookEngine instance with custom configuration.
 * Does not affect the singleton instance.
 * Useful for isolated operations that need different cache/config settings.
 */
export function createScopedEngine(config?: Partial<PlaybookEngineConfig>): PlaybookEngine {
  return new PlaybookEngine(config);
}
